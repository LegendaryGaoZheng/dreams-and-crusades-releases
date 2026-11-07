// priority: 81
// Vinery 葡萄 × FTB Ultimine（连锁破坏）兼容
// 模仿 VanillaCropLikeHandler 对甜浆果/可可豆的处理：
// - 右键范围收获成熟葡萄
// - 收获后把 age 重置为 1
// - 支持地面葡萄丛 GrapeBushBlock 与葡萄藤 GrapeVineBlock
// 只注册 handler，不改 Vinery / FTB Ultimine 本体。

var VineryHandlerClass = Java.loadClass('dev.ftb.mods.ftbultimine.api.crop.CropLikeHandler')
var VineryRegisterEventClass = Java.loadClass('dev.ftb.mods.ftbultimine.api.crop.RegisterCropLikeEvent')
var VineryCropRegistryClass = Java.loadClass('dev.ftb.mods.ftbultimine.crops.CropLikeRegistry')
var VineryItemStackClass = Java.loadClass('net.minecraft.world.item.ItemStack')
var VineryGrapeBushClass = Java.loadClass('net.satisfy.vinery.core.block.GrapeBushBlock')
var VineryGrapeVineClass = Java.loadClass('net.satisfy.vinery.core.block.GrapeVineBlock')
var VineryStemBlockClass = Java.loadClass('net.satisfy.vinery.core.block.StemBlock')
var VinerySoundsClass = Java.loadClass('net.minecraft.sounds.SoundEvents')
var VinerySoundSourceClass = Java.loadClass('net.minecraft.sounds.SoundSource')
var VineryFTBUltimineClass = Java.loadClass('dev.ftb.mods.ftbultimine.FTBUltimine')
var VineryIntegerClass = Java.loadClass('java.lang.Integer')

// 与 Vinery 的 GrapeBushBlock/GrapeVineBlock.useItemOn 保持一致：
// age > 1 才可采；age=3 额外 +1 个；采后 age 重置为 1。
function vineryHarvestCount(level, age) {
  return level.random.nextInt(2) + (age === 3 ? 1 : 0)
}

function vineryIsApplicable(level, pos, state) {
  try {
    var block = state.getBlock()
    if (block instanceof VineryGrapeBushClass) {
      return state.getValue(VineryGrapeBushClass.AGE) > 1
    }
    if (block instanceof VineryGrapeVineClass) {
      if (state.getValue(VineryGrapeVineClass.STERILIZED)) return false
      return state.getValue(VineryGrapeVineClass.AGE) > 1
    }
    if (block instanceof VineryStemBlockClass) {
      // 葡萄藤/棚架（StemBlock、PaleStemBlock、LatticeBlock）
      return block.isMature(state)
    }
  } catch (e) {
    console.warn('[vinery-ultimine] applicable error: ' + e)
  }
  return false
}

// 关键：只有真正按住 FTB Ultimine 连锁键时才由本 handler 处理。
// 不按连锁键时返回 false，让 Vinery 原本的右键种植/采集继续执行。
function vineryUltiminePressed(player) {
  try {
    return VineryFTBUltimineClass.getInstance().getOrCreatePlayerData(player).isPressed()
  } catch (e) {
    return false
  }
}

function vineryDoHarvest(level, pos, state, collector) {
  var block = state.getBlock()
  var age = 0
  var fruit = null

  if (block instanceof VineryGrapeBushClass) {
    age = state.getValue(VineryGrapeBushClass.AGE)
    if (age <= 1) return false
    fruit = block.grapeType().getFruit()
    level.setBlock(pos, state.setValue(VineryGrapeBushClass.AGE, VineryIntegerClass.valueOf(1)), 2)
  } else if (block instanceof VineryGrapeVineClass) {
    if (state.getValue(VineryGrapeVineClass.STERILIZED)) return false
    age = state.getValue(VineryGrapeVineClass.AGE)
    if (age <= 1) return false
    fruit = block.type.getFruit()
    level.setBlock(pos, state.setValue(VineryGrapeVineClass.AGE, VineryIntegerClass.valueOf(1)), 2)
  } else if (block instanceof VineryStemBlockClass) {
    if (!block.isMature(state)) return false
    // StemBlock.dropGrapes 的成熟分支产出 3–4 枚；这里交给 Ultimine 汇总。
    var stemFruit = state.getValue(VineryStemBlockClass.GRAPE).getFruit()
    var stemCount = 3 + level.random.nextInt(2)
    if (!level.setBlock(pos, state.setValue(VineryStemBlockClass.AGE, VineryIntegerClass.valueOf(2)), 2)) return false
    collector.add(new VineryItemStackClass(stemFruit, VineryIntegerClass.valueOf(stemCount)))
    level.playSound(null, pos, VinerySoundsClass.SWEET_BERRY_BUSH_PICK_BERRIES,
      VinerySoundSourceClass.BLOCKS, 1.0, 0.8 + level.random.nextFloat() * 0.4)
    return true
  } else {
    return false
  }

  var count = vineryHarvestCount(level, age)
  if (count > 0) {
    collector.add(new VineryItemStackClass(fruit, VineryIntegerClass.valueOf(count)))
  }
  return true
}

function vineryIsEquivalent(a, b) {
  return String(a.getBlock().builtInRegistryHolder().key().location()) === String(b.getBlock().builtInRegistryHolder().key().location())
}

var VineryCropHandler = new JavaAdapter(VineryHandlerClass, {
  isApplicable: function(level, pos, state) {
    return vineryIsApplicable(level, pos, state)
  },
  doHarvesting: function(player, pos, state, collector) {
    try {
      var pressed = vineryUltiminePressed(player)
      if (!pressed) return false
      return vineryDoHarvest(player.level, pos, state, collector)
    } catch (e) {
      console.warn('[vinery-ultimine] harvest failed: ' + e)
      return false
    }
  },
  isEquivalent: function(a, b) {
    return vineryIsEquivalent(a, b)
  }
})

// 事件监听：FTB Ultimine 每次开始一次连锁操作时会重新注册；
// 直接注册作为兜底，防止事件已经触发过。
try {
  VineryCropRegistryClass.getInstance().registerHandler(VineryCropHandler)
  console.info('[vinery-ultimine] direct handler registered')
} catch (e) {
  console.warn('[vinery-ultimine] direct registration failed: ' + e)
}

try {
  var VineryDispatcher = new JavaAdapter(VineryRegisterEventClass, {
    register: function(dispatcher) {
      dispatcher.registerHandler(VineryCropHandler)
      console.info('[vinery-ultimine] event handler registered')
    }
  })
  VineryRegisterEventClass.REGISTER.register(VineryDispatcher)
  console.info('[vinery-ultimine] RegisterCropLikeEvent listener attached')
} catch (e) {
  console.warn('[vinery-ultimine] event registration failed: ' + e)
}
