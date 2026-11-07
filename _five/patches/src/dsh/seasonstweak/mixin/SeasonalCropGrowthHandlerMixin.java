package dsh.seasonstweak.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.Constant;
import org.spongepowered.asm.mixin.injection.ModifyConstant;

/**
 * DSH_SEASONS_TWEAK P03.
 * Serene Seasons gates out-of-season growth with random.nextInt(6) == 0 (about 1/6).
 * Rewriting that constant 6 -> 2 makes the gate pass 50% of the time.
 * require = 0 -> if Serene Seasons changes the method, the patch silently no-ops instead of crashing.
 */
@Mixin(targets = "sereneseasons.season.SeasonalCropGrowthHandler")
public class SeasonalCropGrowthHandlerMixin {
    @ModifyConstant(method = "onCropGrowth", constant = @Constant(intValue = 6), require = 0)
    private static int dsh$halfChance(int original) {
        return 2;
    }
}
