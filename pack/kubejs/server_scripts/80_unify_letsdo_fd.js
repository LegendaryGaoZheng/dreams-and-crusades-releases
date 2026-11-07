// priority: 80
// 梦想与远征 — Let's Do/Farm & Charm 与 Farmer's Delight 重合作物统一
// 目标：番茄/洋葱及其种子、烂番茄、洋葱汤统一为 Farmer's Delight。
// 重要：Farm & Charm 的物品注册表保留，避免旧存档 missing item / 崩溃；
//       旧物品由本脚本在玩家背包和容器打开时替换为 FD 物品。
// 回滚：删除本文件 + kubejs/data/farm_and_charm/loot_table/blocks/*.json。

const $CROP_ITEM_STACK = Java.loadClass('net.minecraft.world.item.ItemStack')
const $CROP_REGISTRIES = Java.loadClass('net.minecraft.core.registries.BuiltInRegistries')

const UNIFY = {
  'farm_and_charm:tomato': 'farmersdelight:tomato',
  'farm_and_charm:tomato_seeds': 'farmersdelight:tomato_seeds',
  'farm_and_charm:rotten_tomato': 'farmersdelight:rotten_tomato',
  'farm_and_charm:onion': 'farmersdelight:onion',
  'farm_and_charm:onion_soup': 'farmersdelight:onion_soup',
  'farm_and_charm:cooked_bacon': 'farmersdelight:cooked_bacon',
  'farm_and_charm:dog_food': 'farmersdelight:dog_food',
  'farm_and_charm:minced_beef': 'farmersdelight:minced_beef',
  'farm_and_charm:raw_pasta': 'farmersdelight:raw_pasta',
  'farm_and_charm:simple_tomato_soup': 'farmersdelight:tomato_soup',
  'bakery:apple_pie_slice': 'farmersdelight:apple_pie_slice',
  'farm_and_charm:bacon': 'farmersdelight:bacon',
  'farm_and_charm:bacon_with_eggs': 'farmersdelight:bacon_and_eggs',
  'bakery:grilled_bacon_sandwich': 'farmersdelight:bacon_sandwich'
}

const OLD_IDS = Object.keys(UNIFY)

function stackId(stack) {
  if (stack == null || stack.isEmpty()) return null
  return String(stack.getItem().builtInRegistryHolder().key().location())
}

function convertStack(stack) {
  const id = stackId(stack)
  if (id == null || !UNIFY[id]) return null
  const item = $CROP_REGISTRIES.ITEM.get(UNIFY[id])
  if (item == null) return null
  return new $CROP_ITEM_STACK(item, stack.getCount())
}

function convertInventory(inv, label) {
  if (inv == null) return 0
  let slots = 0
  try {
    slots = inv.getSlots()
  } catch (e) {
    try { slots = inv.getContainerSize() } catch (e2) { return 0 }
  }
  let changed = 0
  let cropConvertedStack = null
  for (let cropSlot = 0; cropSlot < slots; cropSlot++) {
    let cropStack = null
    try {
      cropStack = inv.getStackInSlot(cropSlot)
    } catch (e) {
      try { cropStack = inv.getItem(cropSlot) } catch (e2) { continue }
    }
    cropConvertedStack = convertStack(cropStack)
    if (cropConvertedStack != null) {
      try {
        if (inv.setStackInSlot) inv.setStackInSlot(cropSlot, cropConvertedStack)
        else inv.setItem(cropSlot, cropConvertedStack)
      } catch (e) {
        try { inv.setItem(cropSlot, cropConvertedStack) } catch (e2) { continue }
      }
      changed++
    }
  }
  if (changed > 0) {
    console.info(`[crop-unify] ${label}: converted ${changed} stack(s)`)
  }
  return changed
}

// 正在打开的容器菜单（箱子/桶/潜影盒/背包等）也逐格转换。
// 这样可以覆盖 PlayerEvents.chestOpened 没有命中的菜单类型。
function convertOpenMenu(menu, label) {
  if (menu == null) return 0
  let menuSlots = null
  try { menuSlots = menu.slots } catch (e) { return 0 }
  if (menuSlots == null) return 0
  let changed = 0
  let menuConverted = null
  for (let menuSlot = 0; menuSlot < menuSlots.size(); menuSlot++) {
    let slot = menuSlots.get(menuSlot)
    if (slot == null) continue
    try {
      menuConverted = convertStack(slot.getItem())
      if (menuConverted != null) {
        slot.set(menuConverted)
        changed++
      }
    } catch (e) {
      // 只读槽或特殊槽忽略
    }
  }
  if (changed > 0) {
    console.info(`[crop-unify] ${label}: converted ${changed} stack(s)`)
  }
  return changed
}

// 玩家登录时先转一次，之后每 20 tick（约 1 秒）扫描一次；
// 打开容器/右键容器仍会立即扫描，降低常驻 CPU。
var CROP_SCAN_COUNTER = 0

PlayerEvents.loggedIn(event => {
  convertInventory(event.player.inventory, 'login')
})

PlayerEvents.tick(event => {
  const p = event.player
  if (p == null) return
  CROP_SCAN_COUNTER++
  if ((CROP_SCAN_COUNTER % 20) !== 0) return
  convertInventory(p.inventory, 'player')
  try {
    convertOpenMenu(p.openInventory, 'menu')
  } catch (e) {
    // 没有打开菜单时忽略
  }
})

// 箱子/桶/潜影盒等菜单打开时扫描容器库存
;['minecraft:chest', 'minecraft:barrel', 'minecraft:shulker_box', 'minecraft:hopper', 'minecraft:dispenser', 'minecraft:dropper'].forEach(menuId => {
  PlayerEvents.chestOpened(menuId, event => {
    try {
      convertInventory(event.inventory, 'container:' + menuId)
    } catch (e) {
      console.warn('[crop-unify] container scan failed: ' + e)
    }
  })
})

// 右键任何带库存的方块时，也在打开前扫描一次
BlockEvents.rightClicked(event => {
  try {
    const inv = event.block.inventory
    if (inv != null) convertInventory(inv, 'block:' + event.block.id)
  } catch (e) {
    // 大多数普通方块没有库存，忽略即可
  }
})

// 旧物品作为输入的配方：改成 FD。
// 旧物品作为输出的配方：直接删除，不再 replaceOutput，
// 否则会和 FD 原生配方生成两个完全相同的合成表。
ServerEvents.recipes(event => {
  OLD_IDS.forEach(oldId => {
    event.replaceInput({}, oldId, UNIFY[oldId])
    event.remove({ output: oldId })
  })
  // Explicit IDs also cover custom serializers whose outputs KubeJS cannot index.
  ;['farm_and_charm:cutting_board/bacon', 'farm_and_charm:mincer/bacon',
    'farm_and_charm:roaster/bacon_with_eggs', 'farm_and_charm:stove/grilled_bacon_sandwich']
    .forEach(id => event.remove({ id: id }))
  console.info('[crop-unify] recipe inputs rewritten; obsolete outputs removed: ' + OLD_IDS.join(', '))
})

// 清掉旧物品在全部 item tag 中的引用，并把 FD 补到关键 tag
ServerEvents.tags('item', event => {
  OLD_IDS.forEach(oldId => event.removeAllTagsFrom(oldId))

  const add = (tag, ids) => ids.forEach(id => event.add(tag, id))

  add('c:raw_bacon', ['farmersdelight:bacon'])
  add('c:foods/raw_meat', ['farmersdelight:bacon'])
  add('c:foods', ['farmersdelight:bacon', 'farmersdelight:bacon_and_eggs', 'farmersdelight:bacon_sandwich'])
  add('origins:meat', ['farmersdelight:bacon', 'farmersdelight:bacon_and_eggs'])
  add('c:crops/tomato', ['farmersdelight:tomato'])
  add('c:crops/onion', ['farmersdelight:onion'])
  add('c:foods/tomato', ['farmersdelight:tomato'])
  add('c:foods/onion', ['farmersdelight:onion'])
  add('c:foods/vegetable', ['farmersdelight:tomato', 'farmersdelight:onion'])
  add('c:vegetables', ['farmersdelight:tomato', 'farmersdelight:onion'])
  add('c:foods/soup', ['farmersdelight:onion_soup', 'farmersdelight:tomato_soup'])
  add('c:foods/food_poisoning', ['farmersdelight:rotten_tomato'])
  add('c:foods', ['farmersdelight:cooked_bacon', 'farmersdelight:dog_food', 'farmersdelight:minced_beef', 'farmersdelight:raw_pasta', 'farmersdelight:apple_pie_slice', 'farmersdelight:tomato_soup'])
  add('c:foods/cooked_bacon', ['farmersdelight:cooked_bacon'])
  add('c:foods/raw_beef', ['farmersdelight:minced_beef'])
  add('c:foods/pasta', ['farmersdelight:raw_pasta'])
  add('c:foods/pie', ['farmersdelight:apple_pie_slice'])
  add('farmersdelight:sweets', ['farmersdelight:apple_pie_slice'])
  add('minecraft:meat', ['farmersdelight:cooked_bacon', 'farmersdelight:minced_beef', 'farmersdelight:dog_food'])
  add('c:seeds/tomato', ['farmersdelight:tomato_seeds'])
  add('c:seeds', ['farmersdelight:tomato_seeds', 'farmersdelight:onion'])
  add('minecraft:villager_plantable_seeds', ['farmersdelight:tomato_seeds', 'farmersdelight:onion'])
  add('create:upright_on_belt', ['farmersdelight:onion_soup', 'farmersdelight:tomato_soup', 'farmersdelight:dog_food'])
  console.info('[crop-unify] item tags cleaned/added')
})
