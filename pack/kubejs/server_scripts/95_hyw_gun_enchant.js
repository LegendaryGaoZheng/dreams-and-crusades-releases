// P04/P05/P06 (server half): HYW firearm enchantments.
// Triggered by a real bullet spawn (hundred_years_war:bullet), i.e. only when a shot actually happens.
//  P04 durability   : damage the gun 1 point per shot, respect Unbreaking, skip creative, break at 0
//  P05 multishot    : extra bullets with a small spread, no extra ammo
//  P06 piercing     : set the arrow pierce level (BulletEntity extends AbstractArrow)
var HYW_HAND = Java.loadClass('net.minecraft.world.InteractionHand')
var HYW_COMP = Java.loadClass('net.minecraft.core.component.DataComponents')
var HYW_GUNS = { 'hundred_years_war:handgonne': 250, 'hundred_years_war:matchlock': 350 }
var HYW_VEC = Java.loadClass('net.minecraft.world.phys.Vec3')
var HYW_DC = HYW_COMP
var HYW_tick = 0

function hywLog(kind, obj) { obj.kind = kind; console.info('[HYW_PATCH] ' + JSON.stringify(obj)) }

function hywEnchLevel(stack, id) {
  var level = 0
  try {
    var ench = stack.getEnchantments()
    var it = ench.keySet().iterator()
    while (it.hasNext()) {
      var holder = it.next()
      var key = holder.unwrapKey()
      if (key.isPresent() && String(key.get().location()) === id) level = ench.getLevel(holder)
    }
  } catch (e) { level = 0 }
  return level
}

function hywPlayer(owner) {
  if (owner == null) return null
  try { if (String(owner.type) !== 'minecraft:player') return null } catch (e) { return null }
  return owner
}

function hywEnsureMax(stack) {
  var max = HYW_GUNS[String(stack.id)]
  if (max == null) return
  if (Number(stack.getMaxDamage()) > 0) return
  try {
    stack.set(HYW_DC.MAX_DAMAGE, max)
  } catch (e) { hywLog('max_damage_error', { error: String(e) }) }
}

function hywSetPierce(bullet, level) {
  // AbstractArrow#setPierceLevel is private in 1.21.1; the level lives in save data.
  // save -> set byte -> load, then restore position/motion in case load touched them.
  var CT = Java.loadClass('net.minecraft.nbt.CompoundTag')
  var tag = new CT()
  bullet.saveWithoutId(tag)
  tag.putByte('PierceLevel', level)
  var x = bullet.getX(), y = bullet.getY(), z = bullet.getZ()
  var v = bullet.getDeltaMovement()
  var vx = Number(v.x()), vy = Number(v.y()), vz = Number(v.z())
  bullet.load(tag)
  bullet.setPos(x, y, z)
  bullet.setDeltaMovement(new HYW_VEC(vx, vy, vz))
}

function hywApplyDurability(player, stack) {
  var maxDamage = Number(stack.getMaxDamage())
  if (!(maxDamage > 0)) return
  if (player.isCreative()) return
  var unbreaking = hywEnchLevel(stack, 'minecraft:unbreaking')
  if (unbreaking > 0 && Math.random() < (1.0 / (unbreaking + 1))) return
  var current = Number(stack.getDamageValue())
  var next = current + 1
  if (next >= maxDamage) {
    player.setItemInHand(HYW_HAND.MAIN_HAND, Item.of('minecraft:air'))
    try {
      player.level.playSound(null, player.x, player.y, player.z, 'minecraft:item.break', 'minecraft:players', 0.8, 1.0)
    } catch (e) { }
    hywLog('gun_broken', { gun: String(stack.id), max_damage: maxDamage })
  } else {
    stack.setDamageValue(next)
  }
}

function hywMultishot(bullet, level, count, player) {
  if (level <= 0) return 0
  var made = 0
  var spawn = null
  try { spawn = bullet.level } catch (e) { return 0 }
  var BE = null
  try { BE = Java.loadClass('ydmsama.hundred_years_war.main.entity.entities.projectile.BulletEntity') } catch (e) { return 0 }
  for (var i = 0; i < count; i++) {
    try {
      var extra = new BE(bullet.getType(), player, spawn)
      var sign = (i === 0) ? -1 : 1
      var spread = 10.0 * Math.PI / 180.0
      var v = bullet.getDeltaMovement()
      var vx = Number(v.x()), vy = Number(v.y()), vz = Number(v.z())
      var cos = Math.cos(sign * spread), sin = Math.sin(sign * spread)
      extra.setPos(bullet.getX(), bullet.getY(), bullet.getZ())
      extra.setDeltaMovement(new HYW_VEC(vx * cos - vz * sin, vy, vx * sin + vz * cos))
      try { extra.setBaseDamage(Number(bullet.getBaseDamage())) } catch (e) { }
      try { hywSetPierce(extra, Number(bullet.getPierceLevel())) } catch (e) { }
      extra.addTag('dsh_multishot_extra')
      spawn.addFreshEntity(extra)
      made++
    } catch (e) { hywLog('multishot_error', { error: String(e) }) }
  }
  return made
}

// Keep a durability bar on every gun stack, including ones crafted before this patch.
PlayerEvents.tick(function (event) {
  HYW_tick++
  if (HYW_tick % 20 !== 0) return
  try {
    var p = event.player
    if (p == null) return
    hywEnsureMax(p.getMainHandItem())
    hywEnsureMax(p.getOffhandItem())
    var inv = p.getInventory()
    for (var i = 0; i < inv.getContainerSize(); i++) hywEnsureMax(inv.getItem(i))
  } catch (e) { }
})

EntityEvents.spawned('hundred_years_war:bullet', function (event) {
  try {
    var bullet = event.entity
    if (bullet == null) return
    if (bullet.getTags().contains('dsh_multishot_extra')) return
    var player = hywPlayer(bullet.getOwner())
    if (player == null) return
    var stack = player.getMainHandItem()
    hywEnsureMax(stack)
    var gun = String(stack.id)
    var max = HYW_GUNS[gun]
    if (max == null) return

    var pierce = hywEnchLevel(stack, 'minecraft:piercing')
    if (pierce > 0) {
      try { hywSetPierce(bullet, pierce) } catch (e) { hywLog('pierce_error', { error: String(e) }) }
    }
    var multishot = hywEnchLevel(stack, 'minecraft:multishot')
    var made = hywMultishot(bullet, multishot, multishot > 0 ? 2 : 0, player)

    var before = Number(stack.getDamageValue())
    hywApplyDurability(player, stack)
    var after = Number(player.getMainHandItem().getDamageValue())

    hywLog('shot', { gun: gun, damage_before: before, damage_after: after,
      max_damage: Number(stack.getMaxDamage()), pierce: pierce, multishot: multishot, extras: made,
      creative: player.isCreative() })
  } catch (e) { hywLog('error', { error: String(e) }) }
})
