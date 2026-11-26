package io.github.questionableinnovations.langenforcer;

import io.github.questionableinnovations.langenforcer.core.Enforcer;
import io.github.questionableinnovations.langenforcer.judge.Verdict;
import io.github.questionableinnovations.langenforcer.rules.ActiveRules;
import net.minecraft.core.Holder;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageType;
import net.minecraft.world.entity.LivingEntity;

/**
 * Damage for saying the wrong thing. The damage type (data/langenforcer/damage_type) is tagged to bypass armour,
 * armour enchantments, shields and knockback.
 */
final class SpokenWordDamage {
    static final ResourceKey<DamageType> TYPE =
            ResourceKey.create(Registries.DAMAGE_TYPE, ResourceLocation.fromNamespaceAndPath(Enforcer.MODID, "spoken_word"));

    private SpokenWordDamage() {
    }

    static DamageSource source(ServerPlayer player, Verdict verdict, ActiveRules rules) {
        Holder<DamageType> type = player.level().registryAccess().registryOrThrow(Registries.DAMAGE_TYPE).getHolderOrThrow(TYPE);
        Enforcer.DeathMessage msg = Enforcer.deathMessage(verdict, rules);
        return new DamageSource(type) {
            @Override
            public Component getLocalizedDeathMessage(LivingEntity victim) {
                Component who = victim.getDisplayName();
                return msg.required() == null
                        ? Component.translatableWithFallback(msg.key(), msg.fallback(), who)
                        : Component.translatableWithFallback(msg.key(), msg.fallback(), who, msg.required());
            }
        };
    }
}
