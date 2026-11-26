package io.github.questionableinnovations.langenforcer;

import io.github.questionableinnovations.langenforcer.core.Enforcer;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.ModLoadingContext;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.config.ModConfig;

@Mod(Enforcer.MODID)
public final class LangEnforcer {
    private static final int REFRESH_TICKS = 10;

    @SuppressWarnings("removal") // the replacement isn't in every Forge 47.x build this mod supports
    public LangEnforcer() {
        ModLoadingContext.get().registerConfig(ModConfig.Type.COMMON, Config.SPEC);
        Enforcer.init(Config.SETTINGS);
        MinecraftForge.EVENT_BUS.register(this);
    }

    @SubscribeEvent
    public void onPlayerTick(TickEvent.PlayerTickEvent event) {
        if (event.phase == TickEvent.Phase.END && event.player instanceof ServerPlayer player
                && (player.tickCount + player.getId()) % REFRESH_TICKS == 0) {
            Inventories.refresh(player);
        }
    }

    @SubscribeEvent
    public void onLogin(PlayerEvent.PlayerLoggedInEvent event) {
        if (event.getEntity() instanceof ServerPlayer player) Inventories.refresh(player);
    }

    @SubscribeEvent
    public void onLogout(PlayerEvent.PlayerLoggedOutEvent event) {
        Enforcer.forget(event.getEntity().getUUID());
    }

    @SubscribeEvent
    public void onRegisterCommands(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("langenforcer")
                .then(Commands.literal("status")
                        .executes(ctx -> status(ctx.getSource(), ctx.getSource().getPlayerOrException()))
                        .then(Commands.argument("player", EntityArgument.player()).requires(s -> s.hasPermission(2))
                                .executes(ctx -> status(ctx.getSource(), EntityArgument.getPlayer(ctx, "player")))))
                .then(Commands.literal("health").requires(s -> s.hasPermission(2)).executes(ctx -> health(ctx.getSource()))));
    }

    private static int status(CommandSourceStack src, ServerPlayer player) {
        var rules = Inventories.refresh(player);
        String text = Enforcer.status(player.getGameProfile().getName(), rules);
        src.sendSuccess(() -> Component.literal(text), false);
        return rules.isActive() ? 1 : 0;
    }

    private static int health(CommandSourceStack src) {
        String url = Enforcer.settings().sidecarUrl();
        Enforcer.judge().health(url).whenComplete((body, err) -> src.getServer().execute(() -> src.sendSuccess(() -> Component.literal(
                err == null ? "Sidecar " + url + ": " + body : "Sidecar " + url + " unreachable: " + err.getMessage()), false)));
        return 1;
    }
}
