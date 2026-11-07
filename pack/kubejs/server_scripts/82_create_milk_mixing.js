// Let’s Do Compat copies the mixing bowl's item ingredient. Create uses liquid milk.
ServerEvents.recipes(event => {
  const milk = { type: 'neoforge:tag', tag: 'c:milk', amount: 1000 }
  event.remove({ id: 'letsdocompat:create/crafting_bowl/butter' })
  event.custom({
    type: 'create:mixing',
    ingredients: [milk],
    results: [{ id: 'farm_and_charm:butter', count: 4 }]
  }).id('dream_expedition:mixing/butter')
  event.remove({ id: 'letsdocompat:create/crafting_bowl/cake_dough' })
  event.custom({
    type: 'create:mixing',
    ingredients: [{"item": "farm_and_charm:flour"}, {"item": "minecraft:sugar"}, {"tag": "bakery:eggs"}, milk],
    results: [{"id": "bakery:cake_dough", "count": 12}]
  }).id('dream_expedition:mixing/cake_dough')
  event.remove({ id: 'letsdocompat:create/crafting_bowl/oatmeal_with_strawberries' })
  event.custom({
    type: 'create:mixing',
    ingredients: [milk, {"tag": "farm_and_charm:oat"}, {"tag": "farm_and_charm:strawberry"}],
    results: [{"id": "farm_and_charm:oatmeal_with_strawberries", "count": 2}]
  }).id('dream_expedition:mixing/oatmeal_with_strawberries')
})
