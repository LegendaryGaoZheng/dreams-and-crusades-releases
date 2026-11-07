import java.net.InetSocketAddress;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;
import pl.skidam.automodpack_core.GlobalVariables;
import pl.skidam.automodpack_core.config.Jsons;
import pl.skidam.automodpack_core.modpack.ModpackContent;
import pl.skidam.automodpack_core.protocol.DownloadClient;
import pl.skidam.automodpack_core.protocol.netty.NettyServer;
import static pl.skidam.automodpack_core.GlobalVariables.*;

public class AutoModpackPilot {
    static void require(boolean ok, String message) {
        if (!ok) throw new IllegalStateException(message);
    }

    static Map<String, Jsons.ModpackContentFields.ModpackContentItem> generate(Path source) {
        Path host = source.resolve("empty-host");
        try { Files.createDirectories(host); } catch (Exception e) { throw new RuntimeException(e); }
        ThreadPoolExecutor executor = (ThreadPoolExecutor) Executors.newFixedThreadPool(2);
        try {
            ModpackContent content = new ModpackContent("Dreams and Crusades Pilot", source, host,
                Set.of("/kubejs/client_scripts/**", "/config/ftbquests/quests/**"),
                Set.of(), Set.of(), executor);
            require(content.create(), "Native content generation failed");
            hostServer.addPaths(content.pathsMap);
            Map<String, Jsons.ModpackContentFields.ModpackContentItem> entries = new TreeMap<>();
            for (var item : content.list) entries.put(item.file, item);
            return entries;
        } finally {
            executor.shutdownNow();
        }
    }

    static long transfer(Map<String, Jsons.ModpackContentFields.ModpackContentItem> content,
                         Path target, Jsons.ModpackAddresses addresses) throws Exception {
        long total = content.values().stream().mapToLong(item -> Long.parseLong(item.size)).sum();
        var manager = new pl.skidam.automodpack_loader_core.utils.DownloadManager(total);
        try {
            manager.attachDownloadClient(new DownloadClient(addresses, new byte[32], 1, cert -> true));
            for (var item : content.values()) {
                Path dest = target.resolve(item.file.substring(1));
                CompletableFuture<Boolean> done = new CompletableFuture<>();
                manager.download(dest, item.sha1, Long.parseLong(item.size), List.of(),
                    () -> done.complete(true), () -> done.complete(false));
                require(done.get(20, TimeUnit.SECONDS), "Native manager rejected the download");
            }
            return total - manager.getTotalBytesRemaining();
        } finally {
            manager.cancelAllAndShutdown();
        }
    }

    static void rejectCorruption(Jsons.ModpackContentFields.ModpackContentItem item,
                                 Path source, Path target, Jsons.ModpackAddresses addresses) throws Exception {
        byte[] original = Files.readAllBytes(source);
        byte[] wrong = new byte[original.length];
        Arrays.fill(wrong, (byte) 'x');
        Files.write(source, wrong);
        var manager = new pl.skidam.automodpack_loader_core.utils.DownloadManager(original.length);
        try {
            manager.attachDownloadClient(new DownloadClient(addresses, new byte[32], 1, cert -> true));
            CompletableFuture<Boolean> done = new CompletableFuture<>();
            manager.download(target, item.sha1, original.length, List.of(),
                () -> done.complete(true), () -> done.complete(false));
            require(!done.get(20, TimeUnit.SECONDS), "Corrupt object was accepted");
            require(!Files.exists(target), "Rejected object left on disk");
        } finally {
            manager.cancelAllAndShutdown();
            Files.write(source, original);
        }
    }

    static void auditDeletionPolicy(Map<String, Jsons.ModpackContentFields.ModpackContentItem> entries,
                                    Path target, Jsons.ModpackAddresses addresses) throws Exception {
        Path unmanaged = target.resolve("personal-notes.txt");
        Files.writeString(unmanaged, "not present in any published manifest");
        var content = new Jsons.ModpackContentFields(new HashSet<>(entries.values()));
        var updater = new pl.skidam.automodpack_loader_core.client.ModpackUpdater(content, addresses, null, target);
        var manifestField = updater.getClass().getDeclaredField("modpackContentFile");
        manifestField.setAccessible(true);
        manifestField.set(updater, target.resolve("automodpack-content.json"));
        var deletion = updater.getClass().getDeclaredMethod("deleteNonModpackFiles", Jsons.ModpackContentFields.class);
        deletion.setAccessible(true);
        deletion.invoke(updater, content);
        boolean violatesPolicy = !Files.exists(unmanaged);
        Files.writeString(target.getParent().resolve("deletion-policy.txt"),
            "Unmanaged file inside AutoModpack managed directory deleted: " + violatesPolicy
            + "\nRequired policy: delete only paths from previous manifest.\n");
        System.out.println(violatesPolicy
            ? "POLICY_FAIL native_loader_deletes_unmanaged_files_inside_pack"
            : "POLICY_PASS unmanaged_file_preserved");
    }

    public static void main(String[] args) throws Exception {
        Path root = Path.of("").toAbsolutePath();
        require(root.toString().contains(".stage") && root.getFileName().toString().startsWith("native-"),
            "Run inside the dedicated staged fixture");
        System.setProperty("log4j.configurationFile", "log4j2.xml");
        serverConfig = new Jsons.ServerConfigFieldsV2();
        serverConfig.autoExcludeUnnecessaryFiles = false;
        serverConfig.validateSecrets = false;
        serverConfig.bindAddress = "127.0.0.1";
        serverConfig.bindPort = 0;
        clientConfig = new Jsons.ClientConfigFieldsV2();
        knownHosts = new Jsons.KnownHostsFields();
        knownHosts.hosts = new HashMap<>();
        AM_VERSION = "4.0.7";
        MC_VERSION = "1.21.1";
        LOADER = "neoforge";
        LOADER_VERSION = "21.1.264";
        hostServer = new NettyServer();
        try {
            Path input = root;
            Path clientRoot = root.resolve("client");
            Files.createDirectories(input.resolve("kubejs/client_scripts"));
            Files.createDirectories(input.resolve("config/ftbquests/quests"));
            Files.createDirectories(input.resolve("saves/keep"));
            Files.writeString(input.resolve("kubejs/client_scripts/change.js"), "// release one\n");
            Files.writeString(input.resolve("config/ftbquests/quests/old.snbt"), "{ title: 'old' }");
            Files.writeString(input.resolve("options.txt"), "private");
            Files.writeString(input.resolve("saves/keep/private.txt"), "private");
            Map<String, Jsons.ModpackContentFields.ModpackContentItem> first = generate(input);
            require(first.size() == 2, "Personal files included");
            var listener = hostServer.start().orElseThrow();
            var address = (InetSocketAddress) listener.channel().localAddress();
            var addresses = new Jsons.ModpackAddresses(address, address, false);
            {
                long initial = transfer(first, clientRoot, addresses);
                require(initial > 0, "No native transfer");
                require(transfer(first, clientRoot, addresses) == 0, "No-change download");
                Files.writeString(clientRoot.resolve("kubejs/client_scripts/change.js"), "// partial");
                require(transfer(first, clientRoot, addresses) > 0, "Partial file not repaired");
                rejectCorruption(first.get("/kubejs/client_scripts/change.js"),
                    input.resolve("kubejs/client_scripts/change.js"),
                    clientRoot.resolve("corrupt-test.js"), addresses);

                Files.writeString(input.resolve("kubejs/client_scripts/change.js"), "// release two changed\n");
                Files.writeString(input.resolve("kubejs/client_scripts/new.js"), "// new\n");
                Files.delete(input.resolve("config/ftbquests/quests/old.snbt"));
                var second = generate(input);
                require(second.size() == 2 && !second.containsKey("/config/ftbquests/quests/old.snbt"),
                    "Native manifest did not reflect deletion");
                require(!first.get("/kubejs/client_scripts/change.js").sha1.equals(
                    second.get("/kubejs/client_scripts/change.js").sha1), "No changed fingerprint");
                long delta = transfer(second, clientRoot, addresses);
                require(delta > 0, "Missing update transfers");
                auditDeletionPolicy(second, clientRoot, addresses);
                require(Files.readString(input.resolve("options.txt")).equals("private"), "External options changed");
                require(Files.readString(input.resolve("saves/keep/private.txt")).equals("private"), "External save changed");
                // Transport passes do not override the separately recorded deletion policy result.
                System.out.println("PILOT_PASS native_manifest_v1_v2 native_download_manager_tls changed added unchanged_skip personal_exclusion partial_repair corrupt_rejected");
                System.out.println("PILOT_PENDING live_connection_interruption full_pack_update multiplayer");
            }
        } finally {
            hostServer.stop();
        }
    }
}
