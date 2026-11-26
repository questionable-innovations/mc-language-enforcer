package io.github.questionableinnovations.langenforcer;

import io.github.questionableinnovations.langenforcer.core.Enforcer;
import io.github.questionableinnovations.langenforcer.rules.ActiveRules;
import io.github.questionableinnovations.langenforcer.rules.FlagDesign;
import io.github.questionableinnovations.langenforcer.rules.RuleResolver;
import net.minecraft.core.Holder;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.item.BannerItem;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.DyeColor;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.ShieldItem;
import net.minecraft.world.level.block.entity.BannerPattern;

import java.util.ArrayList;
import java.util.List;

/** Reduces an inventory to what the rules care about (1.20.1: banner designs live in block entity NBT). */
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
            String name = stack.hasCustomHoverName() ? stack.getHoverName().getString() : null;
            if (stack.getItem() instanceof BannerItem banner) {
                out.add(new RuleResolver.Carried(name, banner.getColor().getName(), layers(stack)));
            } else if (stack.getItem() instanceof ShieldItem && BlockItem.getBlockEntityData(stack) != null) {
                // A banner applied to a shield keeps its design; the shield's own anvil name is what counts
                out.add(new RuleResolver.Carried(name, ShieldItem.getColor(stack).getName(), layers(stack)));
            } else if (name != null) {
                out.add(new RuleResolver.Carried(name, null, List.of()));
            }
        }
        return out;
    }

    static List<FlagDesign.Layer> layers(ItemStack banner) {
        CompoundTag be = BlockItem.getBlockEntityData(banner);
        if (be == null || !be.contains("Patterns", Tag.TAG_LIST)) return List.of();
        ListTag patterns = be.getList("Patterns", Tag.TAG_COMPOUND);
        List<FlagDesign.Layer> out = new ArrayList<>(patterns.size());
        for (int i = 0; i < patterns.size(); i++) {
            CompoundTag p = patterns.getCompound(i);
            Holder<BannerPattern> pattern = BannerPattern.byHash(p.getString("Pattern"));
            String id = pattern == null ? "?" : pattern.unwrapKey().map(k -> k.location().getPath()).orElse("?");
            out.add(new FlagDesign.Layer(DyeColor.byId(p.getInt("Color")).getName(), id));
        }
        return out;
    }
}
