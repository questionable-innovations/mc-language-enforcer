package io.github.questionableinnovations.langenforcer;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import io.github.questionableinnovations.langenforcer.judge.JudgeClient;
import io.github.questionableinnovations.langenforcer.rules.ActiveRules;
import io.github.questionableinnovations.langenforcer.rules.Languages;
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
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.stream.Collectors;

@Mod(LangEnforcer.MODID)
public final class LangEnforcer {
    public static final String MODID = "langenforcer";
    public static final Logger LOG = LoggerFactory.getLogger("LanguageEnforcer");
    private static final int REFRESH_TICKS = 10;

    private static Languages languages;
    private static final JudgeClient JUDGE = new JudgeClient(LOG);

    @SuppressWarnings("removal") // the replacement isn't in every Forge 47.x build this mod supports
    public LangEnforcer() {
        ModLoadingContext.get().registerConfig(ModConfig.Type.COMMON, Config.SPEC);
        MinecraftForge.EVENT_BUS.register(this);
    }

    public static synchronized Languages languages() {
        if (languages == null) languages = Languages.load();
        return languages;
    }

    public static JudgeClient judge() {
        return JUDGE;
    }

    @SubscribeEvent
    public void onPlayerTick(TickEvent.PlayerTickEvent event) {
        if (event.phase == TickEvent.Phase.END && event.player instanceof ServerPlayer player
                && (player.tickCount + player.getId()) % REFRESH_TICKS == 0) {
            PlayerRules.refresh(player);
        }
    }

    @SubscribeEvent
    public void onLogin(PlayerEvent.PlayerLoggedInEvent event) {
        if (event.getEntity() instanceof ServerPlayer player) PlayerRules.refresh(player);
    }

    @SubscribeEvent
    public void onLogout(PlayerEvent.PlayerLoggedOutEvent event) {
        PlayerRules.forget(event.getEntity().getUUID());
    }

    @SubscribeEvent
    public void onRegisterCommands(RegisterCommandsEvent event) {
        CommandDispatcher<CommandSourceStack> d = event.getDispatcher();
        d.register(Commands.literal("langenforcer")
                .then(Commands.literal("status")
                        .executes(ctx -> status(ctx, ctx.getSource().getPlayerOrException()))
                        .then(Commands.argument("player", EntityArgument.player()).requires(s -> s.hasPermission(2))
                                .executes(ctx -> status(ctx, EntityArgument.getPlayer(ctx, "player")))))
                .then(Commands.literal("health").requires(s -> s.hasPermission(2)).executes(this::health)));
    }

    private static int status(CommandContext<CommandSourceStack> ctx, ServerPlayer player) throws CommandSyntaxException {
        ActiveRules r = PlayerRules.refresh(player);
        String text;
        if (!r.isActive()) {
            text = player.getGameProfile().getName() + " speaks freely.";
        } else {
            StringBuilder sb = new StringBuilder(player.getGameProfile().getName()).append(" is held to: ");
            if (!r.languages().isEmpty()) {
                sb.append(r.languages().stream().map(c -> PlayerRules.describe(c).display()).sorted().collect(Collectors.joining(", ")));
            }
            if (r.rock() > 0) sb.append(r.languages().isEmpty() ? "" : "; ").append("Rock (").append(r.rock()).append(" words)");
            if (r.gadsby()) sb.append("; no letter E");
            if (r.mime()) sb.append("; silence");
            text = sb.toString();
        }
        ctx.getSource().sendSuccess(() -> Component.literal(text), false);
        return r.isActive() ? 1 : 0;
    }

    private int health(CommandContext<CommandSourceStack> ctx) {
        CommandSourceStack src = ctx.getSource();
        String url = Config.SIDECAR_URL.get();
        JUDGE.health(url).whenComplete((body, err) -> src.getServer().execute(() -> src.sendSuccess(() -> Component.literal(
                err == null ? "Sidecar " + url + ": " + body : "Sidecar " + url + " unreachable: " + err.getMessage()), false)));
        return 1;
    }
}
