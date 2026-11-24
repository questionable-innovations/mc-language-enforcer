package io.github.questionableinnovations.langenforcer;

import io.github.questionableinnovations.langenforcer.judge.Verdict;
import io.github.questionableinnovations.langenforcer.rules.ActiveRules;
import net.minecraft.server.level.ServerPlayer;

/** Applies a verdict on the server thread. The hurt flash and sound are the only feedback: no chat, no HUD. */
public final class Punisher {
    private Punisher() {
    }

    public static void apply(ServerPlayer player, Verdict verdict, ActiveRules rules) {
        if (!verdict.violation() || player.isRemoved() || !player.isAlive() || player.isCreative() || player.isSpectator()) return;
        // Rules may have changed while the sidecar thought: dropping the flag mid-sentence gets you off the hook
        if (!PlayerRules.get(player.getUUID()).isActive()) return;
        float amount = Verdict.damage(verdict.severity(), Config.MIN_DAMAGE.get(), Config.MAX_DAMAGE.get());
        if (!Config.LETHAL.get()) amount = Math.min(amount, player.getHealth() - 1.0f);
        if (amount <= 0) return;
        // Speech judged after a recent hit should still land, not vanish into invulnerability frames
        player.invulnerableTime = 0;
        player.hurt(SpokenWordDamage.source(player, verdict, rules), amount);
    }
}
