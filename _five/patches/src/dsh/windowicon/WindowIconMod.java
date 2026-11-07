package dsh.windowicon;

import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.event.lifecycle.FMLClientSetupEvent;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.neoforged.neoforge.common.NeoForge;
import org.lwjgl.glfw.GLFW;
import org.lwjgl.glfw.GLFWImage;
import org.lwjgl.system.MemoryStack;
import org.lwjgl.system.MemoryUtil;
import net.neoforged.fml.loading.FMLPaths;
import java.util.ArrayList;
import java.util.List;

import javax.imageio.ImageIO;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * Replaces the Minecraft window (taskbar) icon with config/dsh_window_icon.png.
 * Client-only cosmetic patch; keeps vanilla icon when the file is missing.
 */
@Mod(value = "dsh_window_icon", dist = Dist.CLIENT)
public class WindowIconMod {
    private static final int[] SIZES = {16, 32, 48, 64, 128, 256};
    private static boolean applied;
    private static boolean registered;

    public WindowIconMod(IEventBus bus) {
        bus.addListener(this::onClientSetup);
    }

    private void onClientSetup(FMLClientSetupEvent event) {
        if (!registered) {
            registered = true;
            NeoForge.EVENT_BUS.addListener(WindowIconMod::onClientTick);
        }
    }

    private static void onClientTick(ClientTickEvent.Post event) {
        if (!applied) {
            applied = applyIcon();
        }
    }

    private static Path iconPath() {
        Path p = FMLPaths.CONFIGDIR.get().resolve("dsh_window_icon.png");
        if (Files.isRegularFile(p)) {
            return p;
        }
        Path q = Path.of("config", "dsh_window_icon", "chicken.png");
        return Files.isRegularFile(q) ? q : p;
    }

    private static boolean applyIcon() {
        try {
            long handle = GLFW.glfwGetCurrentContext();
            if (handle == 0L) {
                return false;
            }
            Path path = iconPath();
            if (!Files.isRegularFile(path)) {
                return true;
            }
            BufferedImage src;
            try (InputStream in = Files.newInputStream(path)) {
                src = ImageIO.read(in);
            }
            if (src == null) {
                return true;
            }
            List<ByteBuffer> allocated = new ArrayList<>();
            try (MemoryStack stack = MemoryStack.stackPush()) {
                GLFWImage.Buffer buffer = GLFWImage.malloc(SIZES.length, stack);
                for (int i = 0; i < SIZES.length; i++) {
                    int size = SIZES[i];
                    BufferedImage scaled = new BufferedImage(size, size, BufferedImage.TYPE_INT_ARGB);
                    Graphics2D g = scaled.createGraphics();
                    g.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BILINEAR);
                    g.setRenderingHint(RenderingHints.KEY_RENDERING, RenderingHints.VALUE_RENDER_QUALITY);
                    g.drawImage(src, 0, 0, size, size, null);
                    g.dispose();
                    ByteBuffer pixels = MemoryUtil.memAlloc(size * size * 4);
                    allocated.add(pixels);
                    for (int y = 0; y < size; y++) {
                        for (int x = 0; x < size; x++) {
                            int argb = scaled.getRGB(x, y);
                            pixels.put((byte) ((argb >> 16) & 0xFF));
                            pixels.put((byte) ((argb >> 8) & 0xFF));
                            pixels.put((byte) (argb & 0xFF));
                            pixels.put((byte) ((argb >>> 24) & 0xFF));
                        }
                    }
                    pixels.flip();
                    buffer.position(i).width(size).height(size).pixels(pixels);
                }
                buffer.position(0);
                GLFW.glfwSetWindowIcon(handle, buffer);
                System.out.println("[DSH_WINDOW_ICON] Applied chicken icon to window " + handle + " from " + path);
            } finally {
                for (ByteBuffer pixels : allocated) MemoryUtil.memFree(pixels);
            }
            return true;
        } catch (Throwable error) {
            System.err.println("[DSH_WINDOW_ICON] Failed to apply icon");
            error.printStackTrace();
            return true;
        }
    }
}
