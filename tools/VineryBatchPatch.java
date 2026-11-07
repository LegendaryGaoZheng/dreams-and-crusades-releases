import java.nio.file.Files;
import java.nio.file.Path;
import org.objectweb.asm.*;

public class VineryBatchPatch implements Opcodes {
    private static final String OWNER = "net/satisfy/vinery/core/block/entity/FermentationBarrelBlockEntity";
    private static final String STACK = "net/minecraft/world/item/ItemStack";
    private static final String TYPE = "net/minecraft/core/component/DataComponentType";
    private static final String YEAR = "net/satisfy/vinery/core/component/WineYearComponent";
    private static final String SUPPLIER = "dev/architectury/registry/registries/RegistrySupplier";
    private static final String PAIR = "(L" + STACK + ";L" + STACK + ";)";
    private static final String RECIPE = "(Lnet/satisfy/vinery/core/recipe/FermentationBarrelRecipe;Lnet/minecraft/core/RegistryAccess;)";
    private static final String ALIGN = "dsh$alignWineYear";
    private static final String FITS = "dsh$fitsWineBatch";

    public static void main(String[] args) throws Exception {
        var reader = new ClassReader(Files.readAllBytes(Path.of(args[0])));
        if (!OWNER.equals(reader.getClassName())) throw new IllegalArgumentException("Unexpected class");
        var writer = new ClassWriter(reader, ClassWriter.COMPUTE_MAXS);
        int[] sites = new int[2];
        reader.accept(new ClassVisitor(ASM9, writer) {
            @Override public MethodVisitor visitMethod(int access, String name, String descriptor, String signature, String[] exceptions) {
                var method = super.visitMethod(access, name, descriptor, signature, exceptions);
                boolean check = name.equals("canCraft") && descriptor.equals(RECIPE + "Z");
                boolean craft = name.equals("craft") && descriptor.equals(RECIPE + "V");
                if (!check && !craft) return method;
                return new MethodVisitor(ASM9, method) {
                    @Override public void visitMethodInsn(int op, String owner, String name, String desc, boolean itf) {
                        if (check && op == INVOKESTATIC && owner.equals(OWNER) && name.equals("fits") && desc.equals(PAIR + "Z")) {
                            sites[0]++;
                            super.visitMethodInsn(op, owner, FITS, desc, false);
                            return;
                        }
                        if (craft && op == INVOKEVIRTUAL && owner.equals(STACK) && name.equals("grow") && desc.equals("(I)V")) {
                            sites[1]++;
                            visitVarInsn(ALOAD, 4);
                            visitVarInsn(ALOAD, 3);
                            super.visitMethodInsn(INVOKESTATIC, OWNER, ALIGN, PAIR + "V", false);
                        }
                        super.visitMethodInsn(op, owner, name, desc, itf);
                    }
                };
            }
        }, 0);
        if (sites[0] != 1 || sites[1] != 1) throw new IllegalStateException("Unexpected patch sites");
        writeHelpers(writer);
        Files.write(Path.of(args[1]), writer.toByteArray());
    }

    private static void writeHelpers(ClassWriter writer) {
        var align = writer.visitMethod(ACC_PRIVATE | ACC_STATIC, ALIGN, PAIR + "V", null, null);
        align.visitCode();
        align.visitFieldInsn(GETSTATIC, "net/satisfy/vinery/core/registry/DataComponentRegistry", "WINE_YEAR", "L" + SUPPLIER + ";");
        align.visitMethodInsn(INVOKEINTERFACE, SUPPLIER, "get", "()Ljava/lang/Object;", true);
        align.visitTypeInsn(CHECKCAST, TYPE);
        align.visitVarInsn(ASTORE, 2);
        align.visitVarInsn(ALOAD, 1);
        align.visitVarInsn(ALOAD, 2);
        align.visitMethodInsn(INVOKEVIRTUAL, STACK, "get", "(L" + TYPE + ";)Ljava/lang/Object;", false);
        align.visitTypeInsn(CHECKCAST, YEAR);
        align.visitVarInsn(ASTORE, 3);
        Label done = new Label();
        align.visitVarInsn(ALOAD, 3);
        align.visitJumpInsn(IFNULL, done);
        align.visitVarInsn(ALOAD, 0);
        align.visitVarInsn(ALOAD, 2);
        align.visitMethodInsn(INVOKEVIRTUAL, STACK, "get", "(L" + TYPE + ";)Ljava/lang/Object;", false);
        align.visitTypeInsn(CHECKCAST, YEAR);
        align.visitVarInsn(ASTORE, 4);
        align.visitVarInsn(ALOAD, 4);
        align.visitJumpInsn(IFNULL, done);
        align.visitVarInsn(ALOAD, 0);
        align.visitVarInsn(ALOAD, 2);
        align.visitVarInsn(ALOAD, 4);
        align.visitVarInsn(ALOAD, 3);
        align.visitMethodInsn(INVOKEVIRTUAL, YEAR, "brewedDay", "()I", false);
        align.visitMethodInsn(INVOKEVIRTUAL, YEAR, "withBrewedDay", "(I)L" + YEAR + ";", false);
        align.visitMethodInsn(INVOKEVIRTUAL, STACK, "set", "(L" + TYPE + ";Ljava/lang/Object;)Ljava/lang/Object;", false);
        align.visitInsn(POP);
        align.visitLabel(done);
        align.visitFrame(F_APPEND, 2, new Object[]{TYPE, YEAR}, 0, null);
        align.visitInsn(RETURN);
        align.visitMaxs(0, 0);
        align.visitEnd();

        var fits = writer.visitMethod(ACC_PRIVATE | ACC_STATIC, FITS, PAIR + "Z", null, null);
        fits.visitCode();
        var compare = new Label();
        fits.visitVarInsn(ALOAD, 0);
        fits.visitMethodInsn(INVOKEVIRTUAL, STACK, "isEmpty", "()Z", false);
        fits.visitJumpInsn(IFNE, compare);
        fits.visitVarInsn(ALOAD, 0);
        fits.visitMethodInsn(INVOKEVIRTUAL, STACK, "copy", "()L" + STACK + ";", false);
        fits.visitVarInsn(ASTORE, 0);
        fits.visitVarInsn(ALOAD, 0);
        fits.visitVarInsn(ALOAD, 1);
        fits.visitMethodInsn(INVOKESTATIC, OWNER, ALIGN, PAIR + "V", false);
        fits.visitLabel(compare);
        fits.visitFrame(F_SAME, 0, null, 0, null);
        fits.visitVarInsn(ALOAD, 0);
        fits.visitVarInsn(ALOAD, 1);
        fits.visitMethodInsn(INVOKESTATIC, OWNER, "fits", PAIR + "Z", false);
        fits.visitInsn(IRETURN);
        fits.visitMaxs(0, 0);
        fits.visitEnd();
    }
}
