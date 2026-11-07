// priority: 110
// 任务书引导：新玩家第一次进世界时给一本 FTB 任务书（物品只给一次，存在玩家 persistentData）
var $ItemStack = Java.loadClass('net.minecraft.world.item.ItemStack')
var $BuiltInRegistries = Java.loadClass('net.minecraft.core.registries.BuiltInRegistries')

var GIVEN = false

PlayerEvents.loggedIn(function (event) {
  try {
    var player = event.player
    var pd = player.persistentData
    if (pd.getBoolean('de_quest_book_given')) return
    // 先尝试直接给物品；失败则用命令兜底
    var item = $BuiltInRegistries.ITEM.get('ftbquests:book')
    var stack = new $ItemStack(item, 1)
    if (!player.addItem(stack)) {
      player.server.runCommandSilent('give ' + player.getName().getString() + ' ftbquests:book 1')
    }
    pd.putBoolean('de_quest_book_given', true)
    player.tell('§6[梦想与远征]§r 已发放任务书：右键打开，先领「启程补给」。')
  } catch (e) {
    console.error('[quests] give book failed: ' + e)
  }
})

ServerEvents.loaded(function (event) {
  try {
    var ids = ['first_scroll','first_camp','first_war','first_capture','five_captures']
    var rl = Java.loadClass('net.minecraft.resources.ResourceLocation')
    var advances = event.server.getAdvancements()
    var found = 0
    for (var i = 0; i < ids.length; i++) {
      if (advances.get(rl.parse('dream_expedition:' + ids[i])) != null) found++
    }
    console.info('[quests] custom advancements loaded: ' + found + '/' + ids.length)
  } catch (e) {
    console.error('[quests] advancement check failed: ' + e)
  }
})
