// DEV TEST ONLY. Exclude from formal releases. Supported KubeJS millisecond clock.
var PM_MC = Java.loadClass('net.minecraft.client.Minecraft')
var PM_CFG = JsonIO.read('config/dsh_perf_run.json')
if (PM_CFG == null || PM_CFG.test_only !== true) throw new Error('Missing isolated measurement config')
global.PERF_SAMPLE = {phase:'idle',generation:0,done:false,failed:false}
var PM_frames = [], PM_summaries = [], PM_last = 0, PM_gen = -1, PM_phase = 'idle', PM_flushed = false, PM_viewport = null, PM_transitions = [], PM_viewportCheck = 0, PM_viewports = []
function PM_summary(name) {
  var rows=PM_frames.filter(function(r){return r[0]===name})
  if (!rows.length) return {phase:name,frames:0,invalid:true}
  var a=rows.map(function(r){return r[2]}).sort(function(a,b){return b-a}), sum=0, s1=0, count100=0, count250=0, count1000=0, stalled=0
  var n1=Math.max(1,Math.ceil(a.length*.01))
  for(var i=0;i<a.length;i++){sum+=a[i];if(i<n1)s1+=a[i];if(a[i]>100){count100++;stalled+=a[i]}if(a[i]>250)count250++;if(a[i]>1000)count1000++}
  return {phase:name,frames:a.length,seconds:sum/1000,avg_fps:1000*a.length/sum,one_percent_low:1000*n1/s1,max_frame_ms:a[0],p99_ms:a[Math.floor(a.length*.01)],stalls100:count100,stalls250:count250,stalls1000:count1000,stall_time_ms:stalled,screen_frames:rows.filter(function(r){return r[3]!==''}).length}
}
NativeEvents.onEvent('net.neoforged.neoforge.client.event.RenderFrameEvent$Pre',function(event){
  var state=global.PERF_SAMPLE, now=Number(Utils.getSystemTime()), mc=PM_MC.getInstance()
  if(mc.level!=null && now>=PM_viewportCheck){
    PM_viewportCheck=now+1000
    var viewport={width:mc.getWindow().getWidth(),height:mc.getWindow().getHeight()}
    if(PM_viewport==null){PM_viewport=viewport;PM_viewports.push(viewport);console.info('[PERF2] VIEWPORT '+JSON.stringify(viewport))}
    else if(viewport.width!==PM_viewport.width || viewport.height!==PM_viewport.height){PM_viewports.push(viewport);state.reason='Viewport resized during measurement';state.failed=true;console.error('[PERF2] VIEWPORT '+JSON.stringify(viewport))}
  }
  if (state.generation!==PM_gen) {
    if(PM_gen>=0 && PM_phase!=='idle' && PM_phase!=='done' && PM_last && now>PM_last){
      PM_frames.push([PM_phase,now,now-PM_last,mc.screen==null?'':'screen_open']);PM_transitions.push({from:PM_phase,to:state.phase,clock_ms:now,dt_ms:now-PM_last})
    }
    if(PM_phase!=='idle' && PM_phase!=='done') {var s=PM_summary(PM_phase);PM_summaries.push(s);console.info('[PERF2] RESULT '+JSON.stringify(s))}
    PM_gen=state.generation;PM_phase=state.phase;PM_last=now
  }
  if(state.done || state.failed){
    if(!PM_flushed){
      PM_flushed=true
      JsonIO.write('config/dsh_perf_result.json',{run:PM_CFG,viewport:PM_viewport,viewports:PM_viewports,transitions:PM_transitions,failed:state.failed,reason:state.reason,summaries:PM_summaries,route:state.route,frame_columns:['phase','clock_ms','dt_ms','screen'],frames:PM_frames})
      console.info('[PERF2] '+(state.failed?'FAILED ':'COMPLETE ')+JSON.stringify({reason:state.reason,summaries:PM_summaries}))
    }
    return
  }
  if(PM_phase==='idle'||PM_phase==='done'){PM_last=now;return}
  if(PM_last){var dt=now-PM_last;if(dt>0)PM_frames.push([PM_phase,now,dt,mc.screen==null?'':'screen_open'])}
  PM_last=now
})
