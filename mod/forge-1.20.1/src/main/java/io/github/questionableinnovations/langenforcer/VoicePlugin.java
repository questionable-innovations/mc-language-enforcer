package io.github.questionableinnovations.langenforcer;

import de.maxhenkel.voicechat.api.ForgeVoicechatPlugin;
import io.github.questionableinnovations.langenforcer.judge.Verdict;
import io.github.questionableinnovations.langenforcer.rules.ActiveRules;
import io.github.questionableinnovations.langenforcer.voice.VoiceListener;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.server.ServerLifecycleHooks;

import java.util.UUID;

@ForgeVoicechatPlugin
public final class VoicePlugin extends VoiceListener {
    @Override
    protected boolean serverRunning() {
        return ServerLifecycleHooks.getCurrentServer() != null;
    }

    @Override
    protected String playerName(UUID id) {
        MinecraftServer server = ServerLifecycleHooks.getCurrentServer();
        ServerPlayer p = server == null ? null : server.getPlayerList().getPlayer(id);
        return p == null ? null : p.getGameProfile().getName();
    }

    @Override
    protected void punish(UUID id, Verdict verdict, ActiveRules rules) {
        MinecraftServer server = ServerLifecycleHooks.getCurrentServer();
        if (server == null) return;
        server.execute(() -> {
            ServerPlayer player = server.getPlayerList().getPlayer(id);
            if (player != null) Punisher.apply(player, verdict, rules);
        });
    }
}
