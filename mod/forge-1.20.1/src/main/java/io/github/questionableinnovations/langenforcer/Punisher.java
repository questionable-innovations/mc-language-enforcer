package io.github.questionableinnovations.langenforcer;

import io.github.questionableinnovations.langenforcer.core.Enforcer;
import io.github.questionableinnovations.langenforcer.judge.Verdict;
import io.github.questionableinnovations.langenforcer.rules.ActiveRules;
import net.minecraft.server.level.ServerPlayer;

/** Applies a verdict on the server thread. The hurt flash and sound are the only feedback: no chat, no HUD. */
final class Punisher {
    private Punisher() {
    }

    static void apply(ServerPlayer player, Verdict verdict, ActiveRules rules) {
        if (player.isRemoved() || !player.isAlive() || player.isCreative() || player.isSpectator()) return;
        float amount = Enforcer.damage(player.getUUID(), verdict, player.getHealth());
        if (amount <= 0) return;
        // Speech judged after a recent hit should still land, not vanish into invulnerability frames
        player.invulnerableTime = 0;
        player.hurt(SpokenWordDamage.source(player, verdict, rules), amount);
    }
}
