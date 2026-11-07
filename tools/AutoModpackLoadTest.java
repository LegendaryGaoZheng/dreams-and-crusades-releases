import java.net.InetSocketAddress;
import java.nio.file.*;
import java.util.*;
import pl.skidam.automodpack_core.GlobalVariables;
import pl.skidam.automodpack_core.config.Jsons;
import pl.skidam.automodpack_core.loader.ModpackLoaderService;
import pl.skidam.automodpack_core.utils.FileInspection;
import pl.skidam.automodpack_loader_core.client.ModpackUpdater;
import pl.skidam.automodpack_loader_core.client.ModpackUtils;
import pl.skidam.automodpack_core.config.ConfigTools;

public class AutoModpackLoadTest {
    public static void main(String[] args) throws Exception {
        Path root = Path.of(args[0]).toAbsolutePath().normalize();
        if (!root.toString().contains(".stage")) throw new IllegalArgumentException("Isolated fixture required");
        Path standard = root.resolve("standard"), managed = root.resolve("managed/mods");
        Files.createDirectories(standard); Files.createDirectories(managed);
        Files.writeString(standard.resolve("duplicate.jar"), "same jar");
        Files.writeString(managed.resolve("duplicate.jar"), "same jar");
        Files.writeString(managed.resolve("needed.jar"), "managed jar");
        Files.writeString(standard.resolve("needed.jar.disabled"), "managed jar");
        Files.writeString(managed.resolve("ignore.txt"), "do not load");
        List<Path> loaded = new ArrayList<>();
        GlobalVariables.preload = true;
        GlobalVariables.MODS_DIR = standard;
        GlobalVariables.MODPACK_LOADER = new ModpackLoaderService() {
            public void loadModpack(List<Path> paths) { loaded.addAll(paths); }
            public List<FileInspection.Mod> getModpackNestedConflicts(Path path) { throw new AssertionError("Unexpected mutation scan"); }
        };
        var address = new InetSocketAddress("127.0.0.1", 6069);
        var updater = new ModpackUpdater(null, new Jsons.ModpackAddresses(address,address,false), null, root.resolve("managed"));
        updater.loadInstalledModpack();
        if (!loaded.equals(List.of(managed.resolve("needed.jar")))) throw new AssertionError("Wrong loaded files " + loaded);
        if (!Files.readString(standard.resolve("duplicate.jar")).equals("same jar")) throw new AssertionError("Standard changed");
        if (!Files.readString(managed.resolve("ignore.txt")).equals("do not load")) throw new AssertionError("Managed changed");
        System.out.println("PASS real loadInstalledModpack: managed JAR loaded, duplicate skipped, files retained");
        String sha = HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-1").digest(Files.readAllBytes(managed.resolve("needed.jar"))));
        var item = new Jsons.ModpackContentFields.ModpackContentItem("/mods/needed.jar", "11", "mod", false, false, sha, "0");
        var content = new Jsons.ModpackContentFields(Set.of(item));
        Path manifest = root.resolve("managed/automodpack-content.json");
        Files.writeString(manifest, ConfigTools.GSON.toJson(content));
        GlobalVariables.clientLocalMetadataFile = root.resolve("metadata.json");
        if (ModpackUtils.isUpdate(content, root.resolve("managed")).requiresUpdate()) throw new AssertionError("Identical file flagged");
        Files.delete(managed.resolve("needed.jar"));
        var missing = ModpackUtils.isUpdate(content, root.resolve("managed"));
        if (!missing.requiresUpdate() || !missing.filesToUpdate().contains(item)) throw new AssertionError("Missing file not detected");
        Files.writeString(managed.resolve("needed.jar"), "wrong data");
        if (!ModpackUtils.isUpdate(content, root.resolve("managed")).requiresUpdate()) throw new AssertionError("Wrong hash not detected");
        System.out.println("PASS real update check: unchanged skipped, missing and changed detected");
    }
}
