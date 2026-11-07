// priority: 80
// 从 Farm & Charm / Bakery 创造模式标签页移除已废弃的重合物。
// 保留注册表，避免旧存档崩溃。

StartupEvents.modifyCreativeTab('farm_and_charm:farm_and_charm', event => {
  event.remove('farm_and_charm:tomato')
  event.remove('farm_and_charm:tomato_seeds')
  event.remove('farm_and_charm:rotten_tomato')
  event.remove('farm_and_charm:onion')
  event.remove('farm_and_charm:onion_soup')
  event.remove('farm_and_charm:cooked_bacon')
  event.remove('farm_and_charm:dog_food')
  event.remove('farm_and_charm:minced_beef')
  event.remove('farm_and_charm:raw_pasta')
  event.remove('farm_and_charm:simple_tomato_soup')
})

StartupEvents.modifyCreativeTab('bakery:bakery', event => {
  event.remove('bakery:apple_pie_slice')
  event.remove('farm_and_charm:bacon')
  event.remove('farm_and_charm:bacon_with_eggs')
  event.remove('bakery:grilled_bacon_sandwich')
})
