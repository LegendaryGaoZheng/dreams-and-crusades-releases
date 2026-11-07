// ISOLATED TEST ONLY. Validate absolute world folder, not editable LevelName.
var PR_CFG=JsonIO.read('config/dsh_perf_run.json')
var PR_ROOT=Java.loadClass('net.minecraft.world.level.storage.LevelResource').ROOT
var PR_active=false, PR_stage=-1, PR_deadline=0, PR_hop=0, PR_nextHop=0, PR_player=null, PR_routes=[], PR_pending=null
function PR_now(){return Number(Utils.getSystemTime())}
function PR_fail(reason){global.PERF_SAMPLE.reason=reason;global.PERF_SAMPLE.failed=true;global.PERF_SAMPLE.phase='done';global.PERF_SAMPLE.generation++;console.error('[PERF2] ROUTE_FAILED '+reason);PR_active=false}
function PR_phase(name,duration){var now=PR_now();global.PERF_SAMPLE.phase=name;global.PERF_SAMPLE.generation++;PR_deadline=now+duration*1000;console.info('[PERF2] PHASE '+JSON.stringify({phase:name,clock_ms:now,x:PR_player.x,y:PR_player.y,z:PR_player.z,duration:duration}))}
function PR_tp(server,x,y,z){
 PR_pending={phase:global.PERF_SAMPLE.phase,hop:PR_hop,x:Number(x),y:Number(y),z:Number(z),requested:PR_now()}
 // KubeJS runCommandSilent returns void; commands can complete after this event.
 server.runCommandSilent('execute in minecraft:overworld run tp @a '+Number(x).toFixed(1)+' '+Number(y).toFixed(1)+' '+Number(z).toFixed(1)+' -90 25')
 return true
}
PlayerEvents.loggedIn(function(event){
 if(PR_active || PR_CFG==null || PR_CFG.test_only!==true)return
 var path=String(event.server.getWorldPath(PR_ROOT).toAbsolutePath().normalize()).replace(/\\/g,'/').replace(/\/$/,'')
 if(path!=='C:/Users/Legen/Desktop/游戏/.minecraft/versions/梦想与远征_dev/saves/perf_oldworld_20261103'){PR_fail('unapproved absolute world '+path);return}
 if(global.PERF_SAMPLE==null){console.error('[PERF2] ROUTE_FAILED startup shared state missing');return}
 PR_player=event.player;PR_active=true;PR_stage=0
 global.PERF_SAMPLE.route=PR_routes
 event.server.runCommandSilent('gamemode spectator @a')
 console.info('[PERF2] ROUTE_READY '+JSON.stringify({path:path,player:String(event.player.username),x:PR_player.x,y:PR_player.y,z:PR_player.z}))
 PR_phase('warmup',Number(PR_CFG.warmup_seconds))
})
ServerEvents.tick(function(event){
 if(!PR_active)return
 var now=PR_now(), duration=Number(PR_CFG.phase_seconds), interval=Number(PR_CFG.hop_interval_ms), hops=Number(PR_CFG.hops)
 if(PR_pending!=null){
  PR_player=event.server.getPlayerList().getPlayers().get(0)
  if(Math.abs(PR_player.x-PR_pending.x)<.1 && Math.abs(PR_player.z-PR_pending.z)<.1){
   var sample={phase:PR_pending.phase,hop:PR_pending.hop,clock_ms:now,x:PR_player.x,y:PR_player.y,z:PR_player.z}
   PR_routes.push(sample);console.info('[PERF2] HOP '+JSON.stringify(sample));PR_pending=null
  } else if(now-PR_pending.requested>15000){PR_fail('teleport coordinate timeout expected='+PR_pending.x+' actual='+PR_player.x)}
  return
 }
 if(PR_stage===0 && now>=PR_deadline){PR_stage=1;PR_phase('base',duration);return}
 if(PR_stage===1 && now>=PR_deadline){PR_stage=2;PR_hop=0;PR_phase('new',duration);PR_nextHop=now+interval;if(!PR_tp(event.server,PR_CFG.route_x,PR_CFG.route_y,PR_CFG.route_z))return;return}
 if((PR_stage===2||PR_stage===4) && PR_hop<hops && now>=PR_nextHop){
  PR_hop++;PR_nextHop=now+interval
  if(!PR_tp(event.server,Number(PR_CFG.route_x)+PR_hop*Number(PR_CFG.step),PR_CFG.route_y,PR_CFG.route_z))return
  return
 }
 if(PR_stage===2 && PR_hop===hops && now>=PR_deadline){PR_stage=3;PR_phase('settle',Number(PR_CFG.settle_seconds));return}
 if(PR_stage===3 && now>=PR_deadline){PR_stage=4;PR_hop=0;PR_phase('loaded',duration);PR_nextHop=now+interval;PR_tp(event.server,PR_CFG.route_x,PR_CFG.route_y,PR_CFG.route_z);return}
 if(PR_stage===4 && PR_hop===hops && now>=PR_deadline){
  PR_stage=5;PR_active=false;global.PERF_SAMPLE.phase='done';global.PERF_SAMPLE.generation++;global.PERF_SAMPLE.done=true
  console.info('[PERF2] ROUTE_COMPLETE '+JSON.stringify({hops_per_phase:hops,route_samples:PR_routes.length,last_x:PR_player.x,last_z:PR_player.z,clock_ms:now}));return
 }
})
