import java.io.BufferedWriter;
import java.io.OutputStreamWriter;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.List;
import java.util.Set;
import jdk.jfr.consumer.RecordedEvent;
import jdk.jfr.consumer.RecordedFrame;
import jdk.jfr.consumer.RecordedMethod;
import jdk.jfr.consumer.RecordedStackTrace;
import jdk.jfr.consumer.RecordedThread;
import jdk.jfr.consumer.RecordingFile;

/** Read-only bounded JSON projection; never expands classloader/module graphs. */
public final class JfrCompact {
    static final Set<String> EVENTS = Set.of(
        "jdk.ExecutionSample", "jdk.NativeMethodSample", "jdk.GCPhasePause",
        "jdk.GarbageCollection", "jdk.ThreadPark", "jdk.JavaMonitorEnter",
        "jdk.JavaMonitorWait", "jdk.SafepointBegin", "jdk.SafepointStateSynchronization",
        "jdk.SafepointCleanup", "jdk.SafepointCleanupTask", "jdk.SafepointEnd");
    static final Set<String> SAMPLES = Set.of("jdk.ExecutionSample", "jdk.NativeMethodSample");
    static final class Counts {
        long read, samples, omittedSamples, durations, missingThreadField, nullThread,
             nullThreadName, missingStackField, nullStack, nullMethod, nullType, truncatedStack;
        String summary() {
            return "JfrCompact read=" + read + " output_render_samples=" + samples
                + " omitted_nonrender_or_unknown_samples=" + omittedSamples
                + " output_all_thread_durations=" + durations
                + " missing_thread_field=" + missingThreadField + " null_thread=" + nullThread
                + " null_thread_name=" + nullThreadName + " missing_stack_field=" + missingStackField
                + " null_stack=" + nullStack + " null_method=" + nullMethod
                + " null_type=" + nullType + " truncated_stack=" + truncatedStack;
        }
    }
    static void quote(BufferedWriter out, String value) throws java.io.IOException {
        if (value == null) { out.write("null"); return; }
        out.write('"');
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '"': out.write("\\\""); break;
                case '\\': out.write("\\\\"); break;
                case '\b': out.write("\\b"); break;
                case '\f': out.write("\\f"); break;
                case '\n': out.write("\\n"); break;
                case '\r': out.write("\\r"); break;
                case '\t': out.write("\\t"); break;
                default:
                    // Escape surrogate code units too: preserves even malformed names as valid JSON.
                    if (c < 0x20 || Character.isSurrogate(c)) {
                        out.write("\\u");
                        for (int shift = 12; shift >= 0; shift -= 4)
                            out.write("0123456789abcdef".charAt((c >>> shift) & 15));
                    } else out.write(c);
            }
        }
        out.write('"');
    }
    static String threadName(RecordedEvent event, String field, Counts counts) {
        if (!event.hasField(field)) { counts.missingThreadField++; return null; }
        RecordedThread thread = event.getThread(field);
        if (thread == null) { counts.nullThread++; return null; }
        String name = thread.getJavaName();
        if (name == null) counts.nullThreadName++;
        return name;
    }
    static void method(BufferedWriter out, String type, String name) throws java.io.IOException {
        out.write("{\"method\":{\"type\":{\"name\":"); quote(out, type);
        out.write("},\"name\":"); quote(out, name); out.write("}}");
    }
    static void stack(BufferedWriter out, RecordedStackTrace trace, Counts counts) throws java.io.IOException {
        stack(out, trace, counts, 32);
    }
    static void stack(BufferedWriter out, RecordedStackTrace trace, Counts counts, int limit) throws java.io.IOException {
        if (trace == null) { counts.nullStack++; out.write("null"); return; }
        List<RecordedFrame> frames = trace.getFrames();
        boolean truncated = trace.isTruncated() || frames.size() > limit;
        if (truncated) counts.truncatedStack++;
        out.write("{\"frames\":[");
        for (int i = 0; i < Math.min(limit, frames.size()); i++) {
            if (i != 0) out.write(',');
            RecordedMethod m = frames.get(i).getMethod();
            // Unknown metadata becomes '?' because the shared stack analyzer expects strings.
            if (m == null) { counts.nullMethod++; method(out, "?", "?"); }
            else {
                String type = "?";
                if (m.getType() == null) counts.nullType++;
                else if (m.getType().getName() != null) type = m.getType().getName();
                method(out, type, m.getName() == null ? "?" : m.getName());
            }
        }
        out.write("],\"truncated\":" + truncated + "}");
    }
    static void event(BufferedWriter out, RecordedEvent event, String kind,
                      String thread, long threadId, boolean selected, boolean sample, Counts counts) throws java.io.IOException {
        out.write("{\"type\":"); quote(out, kind);
        out.write(",\"values\":{\"startTime\":"); quote(out, event.getStartTime().toString());
        if (!sample) { out.write(",\"duration\":"); quote(out, event.getDuration().toString()); }
        out.write(sample ? ",\"sampledThread\":{\"javaName\":" : ",\"eventThread\":{\"javaName\":");
        quote(out, thread); out.write(",\"javaThreadId\":" + threadId + "}");
        if (selected) {
            out.write(",\"stackTrace\":");
            if (!event.hasField("stackTrace")) { counts.missingStackField++; out.write("null"); }
            else stack(out, event.getStackTrace(), counts);
        }
        if (sample && selected) {
            out.write(",\"renderIdentityEvidence\":[");
            boolean firstEvidence = true;
            java.util.Set<String> evidence = new java.util.LinkedHashSet<>();
            RecordedStackTrace trace = event.hasField("stackTrace") ? event.getStackTrace() : null;
            if (trace != null) for (RecordedFrame f : trace.getFrames()) {
                RecordedMethod m = f.getMethod();
                if (m == null || m.getType() == null || m.getType().getName() == null) continue;
                String type = m.getType().getName().replace('/', '.');
                if (strongRenderMethod(type, m.getName()) && evidence.size() < 8)
                    evidence.add(type + "." + m.getName());
            }
            for (String name : evidence) {
                if (!firstEvidence) out.write(','); firstEvidence = false; quote(out, name);
            }
            out.write(']');
        }
        out.write("}}");
    }
    static boolean strongRenderMethod(String type, String name) {
        if (type == null || name == null) return false;
        return (type.equals("net.minecraft.client.Minecraft") && (name.equals("run") || name.equals("runTick")))
            || ((type.equals("net.minecraft.client.renderer.GameRenderer")
                || type.equals("net.minecraft.client.renderer.LevelRenderer")) && name.startsWith("render"));
    }
    static boolean selected(String actualName, long actualId, String wantedName, Long wantedId) {
        return wantedName.equals(actualName) && (wantedId == null || wantedId.longValue() == actualId);
    }
    static final class ThreadStats {
        final String name;
        final long id;
        long samples, renderEvidenceSamples;
        final java.util.ArrayList<RecordedStackTrace> examples = new java.util.ArrayList<>();
        ThreadStats(String name, long id) { this.name = name; this.id = id; }
    }
    static boolean renderEvidence(RecordedStackTrace trace) {
        if (trace == null) return false;
        for (RecordedFrame frame : trace.getFrames()) {
            RecordedMethod m = frame.getMethod();
            if (m == null || m.getType() == null || m.getType().getName() == null) continue;
            String type = m.getType().getName().replace('/', '.');
            if ((type.equals("net.minecraft.client.Minecraft")
                    && ("run".equals(m.getName()) || "runTick".equals(m.getName())))
                    || type.equals("com.mojang.blaze3d.systems.RenderSystem")
                    || type.startsWith("org.lwjgl.opengl.GL")) return true;
        }
        return false;
    }
    static void diagnose(Path path) throws Exception {
        java.util.Map<String, ThreadStats> threads = new java.util.TreeMap<>();
        Counts counts = new Counts();
        try (RecordingFile file = new RecordingFile(path)) {
            while (file.hasMoreEvents()) {
                RecordedEvent e = file.readEvent(); counts.read++;
                if (!SAMPLES.contains(e.getEventType().getName())) continue;
                String name = threadName(e, "sampledThread", counts);
                RecordedThread thread = e.hasField("sampledThread") ? e.getThread("sampledThread") : null;
                long id = thread == null ? -1 : thread.getJavaThreadId();
                String key = id + "\u0000" + name;
                ThreadStats stats = threads.computeIfAbsent(key, k -> new ThreadStats(name, id));
                stats.samples++;
                RecordedStackTrace trace = e.hasField("stackTrace") ? e.getStackTrace() : null;
                if (renderEvidence(trace)) {
                    stats.renderEvidenceSamples++;
                    if (stats.examples.size() < 3) stats.examples.add(trace);
                }
            }
        }
        BufferedWriter out = new BufferedWriter(new OutputStreamWriter(System.out, StandardCharsets.UTF_8));
        out.write("{\"mode\":\"thread_identity_diagnostic\",\"read_events\":" + counts.read
            + ",\"evidence_rule\":\"Minecraft.run/runTick, RenderSystem, or org.lwjgl.opengl.GL* frame; at most 3 stacks per identity\",\"threads\":[");
        boolean first = true;
        for (ThreadStats stats : threads.values()) {
            if (!first) out.write(','); first = false;
            out.write("{\"javaName\":"); quote(out, stats.name);
            out.write(",\"javaThreadId\":" + stats.id + ",\"samples\":" + stats.samples
                + ",\"render_evidence_samples\":" + stats.renderEvidenceSamples + ",\"example_stacks\":[");
            for (int i = 0; i < stats.examples.size(); i++) {
                if (i > 0) out.write(','); stack(out, stats.examples.get(i), counts);
            }
            out.write("]}");
        }
        out.write("]}\n"); out.flush();
        System.err.println("JfrCompact diagnostic identities=" + threads.size() + " " + counts.summary());
    }
    static boolean isLongBlock(String kind, java.time.Duration duration) {
        return (kind.equals("jdk.JavaMonitorEnter") || kind.equals("jdk.ThreadPark"))
            && duration.compareTo(java.time.Duration.ofMillis(100)) >= 0;
    }
    static void renderBlocks(Path path, String name, long id) throws Exception {
        if (id <= 0) throw new IllegalArgumentException("positive Java thread id required");
        Counts counts = new Counts();
        long emitted = 0, missingMonitor = 0, nullMonitor = 0, missingOwner = 0, nullOwner = 0;
        BufferedWriter out = new BufferedWriter(new OutputStreamWriter(System.out, StandardCharsets.UTF_8), 65536);
        try (RecordingFile file = new RecordingFile(path)) {
            out.write('[');
            while (file.hasMoreEvents()) {
                RecordedEvent e = file.readEvent(); counts.read++;
                String kind = e.getEventType().getName();
                if (!isLongBlock(kind, e.getDuration())) continue;
                String actualName = threadName(e, "eventThread", counts);
                RecordedThread thread = e.hasField("eventThread") ? e.getThread("eventThread") : null;
                if (thread == null || !selected(actualName, thread.getJavaThreadId(), name, id)) continue;
                if (emitted++ > 0) out.write(",\n");
                out.write("{\"type\":"); quote(out, kind);
                out.write(",\"values\":{\"startTime\":"); quote(out, e.getStartTime().toString());
                out.write(",\"duration\":"); quote(out, e.getDuration().toString());
                out.write(",\"eventThread\":{\"javaName\":"); quote(out, actualName);
                out.write(",\"javaThreadId\":" + thread.getJavaThreadId() + "},\"stackTrace\":");
                if (!e.hasField("stackTrace")) { counts.missingStackField++; out.write("null"); }
                else stack(out, e.getStackTrace(), counts, 64);
                if (kind.equals("jdk.JavaMonitorEnter")) {
                    if (!e.hasField("monitorClass")) missingMonitor++;
                    else {
                        jdk.jfr.consumer.RecordedClass cls = e.getClass("monitorClass");
                        if (cls == null) nullMonitor++;
                        else { out.write(",\"monitorClass\":{\"name\":"); quote(out, cls.getName()); out.write('}'); }
                    }
                    if (!e.hasField("previousOwner")) missingOwner++;
                    else {
                        RecordedThread owner = e.getThread("previousOwner");
                        if (owner == null) nullOwner++;
                        else {
                            out.write(",\"previousOwner\":{\"javaName\":"); quote(out, owner.getJavaName());
                            out.write(",\"javaThreadId\":" + owner.getJavaThreadId() + "}");
                        }
                    }
                }
                out.write("}}");
            }
            out.write("]\n"); out.flush();
        } finally {
            System.err.println("JfrCompact render-blocks output=" + emitted + " threshold_ms=100 frame_limit=64"
                + " missing_monitor_field=" + missingMonitor + " null_monitor=" + nullMonitor
                + " missing_previous_owner_field=" + missingOwner + " null_previous_owner=" + nullOwner
                + " " + counts.summary());
        }
    }
    static void selfTest() throws Exception {
        if (!isLongBlock("jdk.JavaMonitorEnter", java.time.Duration.ofMillis(100))
                || !isLongBlock("jdk.ThreadPark", java.time.Duration.ofMillis(101))
                || isLongBlock("jdk.ThreadPark", java.time.Duration.ofMillis(99))
                || isLongBlock("jdk.JavaMonitorWait", java.time.Duration.ofSeconds(1)))
            throw new AssertionError("block type and inclusive 100ms threshold");
        if (!selected("main", 3, "main", 3L) || selected("main", 4, "main", 3L)
                || selected("Server thread", 3, "main", 3L) || selected("main", 3, "Render thread", null)
                || !selected("Render thread", 9, "Render thread", null))
            throw new AssertionError("explicit AND identity selection");
        if (!strongRenderMethod("net.minecraft.client.Minecraft", "runTick")
                || !strongRenderMethod("net.minecraft.client.renderer.GameRenderer", "render")
                || strongRenderMethod("net.minecraft.client.Minecraft", "<init>")
                || strongRenderMethod("org.lwjgl.opengl.GL", "<clinit>"))
            throw new AssertionError("strong phase render evidence");
        StringWriter text = new StringWriter();
        BufferedWriter out = new BufferedWriter(text);
        quote(out, "\"\\\b\f\n\r\t\u0000\u001f中\ud83d\ude00\ud800"); out.flush();
        String expected = "\"\\\"\\\\\\b\\f\\n\\r\\t\\u0000\\u001f中\\ud83d\\ude00\\ud800\"";
        if (!text.toString().equals(expected)) throw new AssertionError("JSON escape fixture");
        text.getBuffer().setLength(0);
        Counts counts = new Counts();
        stack(out, null, counts); out.flush();
        if (!text.toString().equals("null") || counts.nullStack != 1)
            throw new AssertionError("null stack fixture");
        text.getBuffer().setLength(0);
        method(out, "a/b", "x\"\n"); out.flush();
        if (!text.toString().equals("{\"method\":{\"type\":{\"name\":\"a/b\"},\"name\":\"x\\\"\\n\"}}"))
            throw new AssertionError("minimal method fixture");
        System.out.println("{\"self_test\":\"PASS\",\"scope\":\"in-memory escaping, null stack, minimal method, exact name/id AND selection, strong render method rules; no recording opened\"}");
    }
    public static void main(String[] args) throws Exception {
        if (args.length == 1 && args[0].equals("--self-test")) { selfTest(); return; }
        if (args.length == 2 && args[0].equals("--diagnose-threads")) { diagnose(Path.of(args[1])); return; }
        if (args.length == 4 && args[0].equals("--render-blocks")) {
            renderBlocks(Path.of(args[1]), args[2], Long.parseLong(args[3])); return;
        }
        if (args.length != 1 && args.length != 5)
            throw new IllegalArgumentException("usage: JfrCompact profile.jfr [--render-thread-name NAME --render-thread-id ID] | --diagnose-threads profile.jfr | --self-test");
        String wantedName = "Render thread";
        Long wantedId = null;
        if (args.length == 5) {
            if (!args[1].equals("--render-thread-name") || !args[3].equals("--render-thread-id"))
                throw new IllegalArgumentException("explicit identity requires name and id together");
            wantedName = args[2]; wantedId = Long.valueOf(args[4]);
            if (wantedId <= 0) throw new IllegalArgumentException("thread id must be positive");
        }
        Counts counts = new Counts();
        BufferedWriter out = new BufferedWriter(new OutputStreamWriter(System.out, StandardCharsets.UTF_8), 65536);
        try (RecordingFile recording = new RecordingFile(Path.of(args[0]))) {
            out.write('[');
            boolean first = true;
            while (recording.hasMoreEvents()) {
                RecordedEvent e = recording.readEvent(); counts.read++;
                String kind = e.getEventType().getName();
                if (!EVENTS.contains(kind)) continue;
                boolean sample = SAMPLES.contains(kind);
                String thread = threadName(e, sample ? "sampledThread" : "eventThread", counts);
                String field = sample ? "sampledThread" : "eventThread";
                RecordedThread rawThread = e.hasField(field) ? e.getThread(field) : null;
                long threadId = rawThread == null ? -1 : rawThread.getJavaThreadId();
                boolean isSelected = selected(thread, threadId, wantedName, wantedId);
                if (sample && !isSelected) { counts.omittedSamples++; continue; }
                if (!first) out.write(",\n");
                event(out, e, kind, thread, threadId, isSelected, sample, counts);
                first = false;
                if (sample) counts.samples++; else counts.durations++;
            }
            out.write("]\n"); out.flush();
        } finally { System.err.println(counts.summary()); }
    }
}
