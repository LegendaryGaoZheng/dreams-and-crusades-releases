// priority: 80
// 把已废弃的 Farm & Charm / Bakery 重合物从 JEI 中隐藏。
// 注册表仍然保留，旧存档不会 missing item。
// KubeJS 2101 使用 RecipeViewerEvents，而不是旧版 JEIEvents。

RecipeViewerEvents.removeEntries('item', event => {
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
  event.remove('bakery:apple_pie_slice')
  event.remove('farm_and_charm:bacon')
  event.remove('farm_and_charm:bacon_with_eggs')
  event.remove('bakery:grilled_bacon_sandwich')
})
