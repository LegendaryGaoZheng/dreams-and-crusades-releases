// Explain Bakery block interactions which its JEI plugin does not index.
RecipeViewerEvents.addInformation('item', event => {
  const foods = {
  "bakery:sweet_dough": [
    "放置甜面团进行方块加工。用擀面杖擀平，或用面包刀在适当阶段切分。",
    "在烘焙台和果酱锅可查询常规配方；桌面蛋糕坯的操作在方块上完成。"
  ],
  "bakery:sponge_sheet": [
    "在农夫魅力的炉灶用蛋糕面团和糖烘焙海绵蛋糕片。",
    "海绵蛋糕片可作为工作台版巧克力蛋糕的蛋糕坯。"
  ],
  "bakery:apple_cupcake": [
    "在世界里用苹果酱右键切分后的纸杯蛋糕坯。",
    "原生操作会返还空罐。"
  ],
  "bakery:chocolate_cake": [
    "在世界里用巧克力松露右键完整蛋糕坯。",
    "也可在工作台无序合成：海绵蛋糕片 + 巧克力松露。"
  ],
  "bakery:chocolate_cake_slice": [
    "在世界里用巧克力松露右键完整蛋糕坯。",
    "将完成的蛋糕放置后分切或食用。"
  ],
  "bakery:chocolate_gateau": [
    "在世界里用巧克力酱右键完整蛋糕坯。",
    "原生操作会返还空罐。"
  ],
  "bakery:chocolate_gateau_slice": [
    "在世界里用巧克力酱右键完整蛋糕坯。",
    "原生操作会返还空罐。",
    "将完成的蛋糕放置后分切或食用。"
  ],
  "bakery:strawberry_cake": [
    "在世界里用草莓酱右键完整蛋糕坯。",
    "原生操作会返还空罐。"
  ],
  "bakery:strawberry_cake_slice": [
    "在世界里用草莓酱右键完整蛋糕坯。",
    "原生操作会返还空罐。",
    "将完成的蛋糕放置后分切或食用。"
  ],
  "bakery:strawberry_cupcake": [
    "在世界里用草莓酱右键切分后的纸杯蛋糕坯。",
    "原生操作会返还空罐。"
  ],
  "bakery:sweetberry_cake": [
    "在世界里用甜浆果酱右键完整蛋糕坯。",
    "原生操作会返还空罐。"
  ],
  "bakery:sweetberry_cake_slice": [
    "在世界里用甜浆果酱右键完整蛋糕坯。",
    "原生操作会返还空罐。",
    "将完成的蛋糕放置后分切或食用。"
  ],
  "bakery:sweetberry_cupcake": [
    "在世界里用甜浆果酱右键切分后的纸杯蛋糕坯。",
    "原生操作会返还空罐。"
  ]
}
  Object.keys(foods).forEach(id => event.add(id, foods[id].map(line => Text.of(line))))
})
