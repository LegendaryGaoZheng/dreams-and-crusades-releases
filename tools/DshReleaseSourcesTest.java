package pl.skidam.automodpack_loader_core.client;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import com.google.gson.*;
import pl.skidam.automodpack_core.config.Jsons;
import pl.skidam.automodpack_loader_core.utils.DownloadManager;
public class DshReleaseSourcesTest {
 public static void main(String[] args) throws Exception {
  Path index=Path.of(args[0]); Path output=Path.of(args[1]);
  var root=JsonParser.parseString(Files.readString(index)).getAsJsonObject();
  var row=root.getAsJsonObject("objects").entrySet().iterator().next();
  long size=row.getValue().getAsJsonObject().get("size").getAsLong();
  var item=new Jsons.ModpackContentFields.ModpackContentItem("/probe.json",String.valueOf(size),"other",false,false,row.getKey(),null);
  DshReleaseSources.refresh();
  var urls=DshReleaseSources.urls(item);
  if(urls.isEmpty())throw new IllegalStateException("No published GitHub source");
  var manager=new DownloadManager(size);
  try {
   var done=new CompletableFuture<Boolean>();
   manager.download(output,item.sha1,size,urls,()->done.complete(true),()->done.complete(false));
   if(!done.get(45,TimeUnit.SECONDS))throw new IllegalStateException("GitHub native download failed");
  }finally{manager.cancelAllAndShutdown();}
  String hash=pl.skidam.automodpack_core.utils.CustomFileUtils.getHash(output);
  if(!hash.equals(item.sha1))throw new IllegalStateException("Hash mismatch");
  var wrong=new Jsons.ModpackContentFields.ModpackContentItem("/probe.json",String.valueOf(size+1),"other",false,false,row.getKey(),null);
  if(!DshReleaseSources.urls(wrong).isEmpty())throw new IllegalStateException("Size guard");
  String bad=Files.readString(index).replace("https://github.com/LegendaryGaoZheng/dreams-and-crusades-releases/releases/download/","https://example.invalid/");
  try {DshReleaseSources.load(bad);throw new IllegalStateException("Outside source allowed");}
  catch(IllegalArgumentException expected){}
  System.out.println("PASS actual_GitHub_release_download native_hash size_guard foreign_repository_rejection");
 }
}
