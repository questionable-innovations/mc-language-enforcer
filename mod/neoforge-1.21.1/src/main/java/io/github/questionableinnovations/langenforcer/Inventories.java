package io.github.questionableinnovations.langenforcer;

import io.github.questionableinnovations.langenforcer.core.Enforcer;
import io.github.questionableinnovations.langenforcer.rules.ActiveRules;
import io.github.questionableinnovations.langenforcer.rules.FlagDesign;
import io.github.questionableinnovations.langenforcer.rules.RuleResolver;
import net.minecraft.core.component.DataComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.item.BannerItem;
import net.minecraft.world.item.DyeColor;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.ShieldItem;
import net.minecraft.world.level.block.entity.BannerPatternLayers;

import java.util.ArrayList;
import java.util.List;

/** Reduces an inventory to what the rules care about (1.21: banner designs live in data components). */
final class Inventories {
    private Inventories() {
    }

    /** Server thread only: inventories are not safe to touch off-thread. */
    static ActiveRules refresh(ServerPlayer player) {
        return Enforcer.refresh(player.getUUID(), carried(player.getInventory()));
    }

    static List<RuleResolver.Carried> carried(Inventory inv) {
        List<RuleResolver.Carried> out = new ArrayList<>();
        for (int i = 0; i < inv.getContainerSize(); i++) {
            ItemStack stack = inv.getItem(i);
            if (stack.isEmpty()) continue;
            Component custom = stack.get(DataComponents.CUSTOM_NAME);
            String name = custom == null ? null : custom.getString();
            DyeColor shieldBase = stack.get(DataComponents.BASE_COLOR);
            if (stack.getItem() instanceof BannerItem banner) {
                out.add(new RuleResolver.Carried(name, banner.getColor().getName(), layers(stack)));
            } else if (stack.getItem() instanceof ShieldItem && shieldBase != null) {
                // A banner applied to a shield keeps its design; the shield's own anvil name is what counts
                out.add(new RuleResolver.Carried(name, shieldBase.getName(), layers(stack)));
            } else if (name != null) {
                out.add(new RuleResolver.Carried(name, null, List.of()));
            }
        }
        return out;
    }

    static List<FlagDesign.Layer> layers(ItemStack banner) {
        BannerPatternLayers patterns = banner.getOrDefault(DataComponents.BANNER_PATTERNS, BannerPatternLayers.EMPTY);
        List<FlagDesign.Layer> out = new ArrayList<>(patterns.layers().size());
        for (BannerPatternLayers.Layer layer : patterns.layers()) {
            String id = layer.pattern().unwrapKey().map(k -> k.location().getPath()).orElse("?");
            out.add(new FlagDesign.Layer(layer.color().getName(), id));
        }
        return out;
    }
}
