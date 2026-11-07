// priority: 88
// 让 HYW 火枪的"快速装填"真正缩短开火冷却（手铳 100 tick / 燧发枪 120 tick）
var QC_LAST = {}
var QC_BASE = {
  'hundred_years_war:handgonne': 100,
  'hundred_years_war:matchlock': 120
}

function qcItemId(stack) {
  return String(stack.getItem().builtInRegistryHolder().key().location())
}

function qcLevel(stack) {
  var lvl = 0
  var ench = stack.getEnchantments()
  var it = ench.keySet().iterator()
  while (it.hasNext()) {
    var holder = it.next()
    var key = holder.unwrapKey()
    if (key.isPresent() && String(key.get().location()) === 'minecraft:quick_charge') {
      lvl = ench.getLevel(holder)
    }
  }
  return lvl
}

PlayerEvents.tick(function (event) {
  var p = event.player
  if (p == null) return
  var stack = p.mainHandItem
  if (!stack || stack.isEmpty()) return
  var id = qcItemId(stack)
  var base = QC_BASE[id]
  if (!base) return
  var cd = p.getCooldowns()
  var on = cd.isOnCooldown(stack.getItem())
  var key = String(p.uuid) + '|' + id
  var was = QC_LAST[key] || false
  QC_LAST[key] = on
  if (!on || was) return
  var lvl = qcLevel(stack)
  if (lvl <= 0) return
  var ticks = Math.max(1, Math.round(base * (1 - 0.2 * lvl)))
  cd.addCooldown(stack.getItem(), ticks)
  console.info('[hyw-quick-charge] ' + p.getName().getString() + ' ' + id + ' lvl=' + lvl + ' cooldown=' + ticks + '/' + base)
})
