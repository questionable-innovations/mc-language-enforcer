package io.github.questionableinnovations.langenforcer;

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

import java.util.stream.Collectors;

/**
 * Damage for saying the wrong thing. The damage type (data/langenforcer/damage_type) is tagged to bypass armour,
 * armour enchantments, shields and knockback. Death messages carry English fallbacks because clients usually
 * don't have this server-only mod's language file.
 */
public final class SpokenWordDamage {
    @SuppressWarnings("removal") // the replacement isn't in every Forge 47.x build this mod supports
    public static final ResourceKey<DamageType> TYPE =
            ResourceKey.create(Registries.DAMAGE_TYPE, new ResourceLocation(LangEnforcer.MODID, "spoken_word"));

    private SpokenWordDamage() {
    }

    public static DamageSource source(ServerPlayer player, Verdict verdict, ActiveRules rules) {
        Holder<DamageType> type = player.level().registryAccess().registryOrThrow(Registries.DAMAGE_TYPE).getHolderOrThrow(TYPE);
        String rule = verdict.rule() == null ? "language" : verdict.rule();
        String required = rules.languages().stream().map(c -> PlayerRules.describe(c).name()).sorted().collect(Collectors.joining(" or "));
        return new DamageSource(type) {
            @Override
            public Component getLocalizedDeathMessage(LivingEntity victim) {
                Component who = victim.getDisplayName();
                return switch (rule) {
                    case "rock" -> Component.translatableWithFallback("death.attack.langenforcer.rock",
                            "%s used too many big words", who);
                    case "gadsby" -> Component.translatableWithFallback("death.attack.langenforcer.gadsby",
                            "%s said a word with an E in it", who);
                    case "mime" -> Component.translatableWithFallback("death.attack.langenforcer.mime",
                            "%s broke the vow of silence", who);
                    default -> required.isEmpty()
                            ? Component.translatableWithFallback("death.attack.langenforcer.basic", "%s spoke out of turn", who)
                            : Component.translatableWithFallback("death.attack.langenforcer.language", "%s forgot to speak %s", who, required);
                };
            }
        };
    }
}
