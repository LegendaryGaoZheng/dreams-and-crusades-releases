import java.nio.file.*;
import org.apache.maven.artifact.versioning.DefaultArtifactVersion;
import net.neoforged.neoforgespi.language.MavenVersionAdapter;

/** Use the installed FML parser, not a Python approximation of version ranges. */
public class ModVersionCheck {
    public static void main(String[] args) throws Exception {
        boolean failed = false;
        for (String line : Files.readAllLines(Path.of(args[0]))) {
            String[] row = line.split("\t", -1);
            boolean ok = MavenVersionAdapter.createFromVersionSpec(row[2]).containsVersion(new DefaultArtifactVersion(row[3]));
            System.out.println((ok ? "PASS" : "FAIL") + " " + row[0] + " requires " + row[1] + " " + row[2] + "; installed " + row[3]);
            failed |= !ok;
        }
        if (failed) System.exit(1);
    }
}
