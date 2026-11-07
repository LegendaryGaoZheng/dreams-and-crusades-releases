package pl.skidam.automodpack_loader_core.client;

import com.google.gson.*;
import java.net.URI;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.*;
import pl.skidam.automodpack_core.config.Jsons;
import static pl.skidam.automodpack_core.GlobalVariables.LOGGER;

public final class DshReleaseSources {
    private static final String BASE = "https://github.com/LegendaryGaoZheng/dreams-and-crusades-releases/releases/download/";
    private static final String INDEX = "https://raw.githubusercontent.com/LegendaryGaoZheng/dreams-and-crusades-releases/main/update-sources.json";
    private static volatile Map<String, Entry> entries = Map.of();
    private record Entry(long size, List<String> urls) {}

    private DshReleaseSources() {}

    public static void refresh() {
        entries = Map.of();
        try {
            HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5))
                .followRedirects(HttpClient.Redirect.NORMAL).build();
            var request = HttpRequest.newBuilder(URI.create(INDEX))
                .timeout(Duration.ofSeconds(10)).GET().build();
            var response = client.send(request, HttpResponse.BodyHandlers.ofInputStream());
            try (var body = response.body()) {
                if (response.statusCode() != 200) throw new IllegalStateException("Index HTTP " + response.statusCode());
                byte[] bytes = body.readNBytes(4 * 1024 * 1024 + 1);
                if (bytes.length > 4 * 1024 * 1024) throw new IllegalStateException("Index too large");
                load(new String(bytes, StandardCharsets.UTF_8));
            }
        } catch (Exception error) {
            if (error instanceof InterruptedException) Thread.currentThread().interrupt();
            LOGGER.warn("[Dreams & Crusades] GitHub source index unavailable; using original sources: {}", error.toString());
        }
    }

    static void load(String json) {
        Map<String, Entry> parsed = new HashMap<>();
        var root = JsonParser.parseString(json).getAsJsonObject();
        if (root.get("format").getAsInt() != 1) throw new IllegalArgumentException("Index format");
        if (!root.get("repository").getAsString().equals("LegendaryGaoZheng/dreams-and-crusades-releases"))
            throw new IllegalArgumentException("Index owner");
        for (var row : root.getAsJsonObject("objects").entrySet()) {
            if (!row.getKey().matches("[a-f0-9]{40}")) throw new IllegalArgumentException("Object hash");
            var object = row.getValue().getAsJsonObject();
            long size = object.get("size").getAsLong();
            if (size < 0) throw new IllegalArgumentException("Object size");
            var urls = new ArrayList<String>();
            for (var value : object.getAsJsonArray("urls")) {
                String url = value.getAsString();
                URI uri = URI.create(url);
                if (!url.startsWith(BASE) || !"github.com".equals(uri.getHost()) || uri.getUserInfo() != null
                        || uri.getFragment() != null || uri.getQuery() != null || url.contains("/../"))
                    throw new IllegalArgumentException("Release URL outside approved project");
                urls.add(url);
            }
            parsed.put(row.getKey(), new Entry(size, List.copyOf(urls)));
        }
        entries = Map.copyOf(parsed);
    }

    public static List<String> urls(Jsons.ModpackContentFields.ModpackContentItem item) {
        Entry entry = entries.get(item.sha1);
        if (entry == null || entry.size != Long.parseLong(item.size)) return List.of();
        return entry.urls;
    }
}
