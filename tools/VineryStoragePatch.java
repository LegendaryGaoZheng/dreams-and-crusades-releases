import java.nio.file.Files;
import java.nio.file.Path;
import org.objectweb.asm.*;

public class VineryStoragePatch implements Opcodes {
    private static final String ITEM = "net/minecraft/world/item/BlockItem";
    private static final String BLOCK = "net/minecraft/world/level/block/Block";
    private static final String STATE = "net/minecraft/world/level/block/state/BlockState";
    private static final String PARENT = "net/satisfy/foundation/storage/BottleGroupRenderer";
    private static final String HELPER = "net/satisfy/vinery/client/render/block/storage/DshBottleState";
    private static final String RESOLVE = "(L" + ITEM + ";)L" + STATE + ";";

    public static void main(String[] args) throws Exception {
        if (args[0].equals("helper")) {
            Files.write(Path.of(args[1]), helper());
            return;
        }
        ClassReader reader = new ClassReader(Files.readAllBytes(Path.of(args[0])));
        String owner = reader.getClassName();
        if (!(owner.endsWith("/BottleRenderer") || owner.endsWith("/BigBottleRenderer")
                || owner.endsWith("/WineBoxRenderer")))
            throw new IllegalArgumentException(owner);
        ClassWriter writer = new ClassWriter(reader, 0);
        int[] sites = {0};
        reader.accept(new ClassVisitor(ASM9, writer) {
            @Override
            public MethodVisitor visitMethod(int access, String name, String descriptor,
                                             String signature, String[] exceptions) {
                MethodVisitor target = super.visitMethod(access, name, descriptor, signature, exceptions);
                if (!name.equals("render")) return target;
                return new MethodVisitor(ASM9, target) {
                    boolean pending;
                    @Override
                    public void visitMethodInsn(int opcode, String owner, String name,
                                                String descriptor, boolean isInterface) {
                        if (pending) {
                            if (opcode != INVOKEVIRTUAL || !owner.equals(BLOCK)
                                    || !name.equals("defaultBlockState")
                                    || !descriptor.equals("()L" + STATE + ";"))
                                throw new IllegalStateException("Unexpected getBlock consumer");
                            super.visitMethodInsn(INVOKESTATIC, HELPER, "resolve", RESOLVE, false);
                            pending = false;
                            sites[0]++;
                        } else if (opcode == INVOKEVIRTUAL && owner.equals(ITEM)
                                && name.equals("getBlock") && descriptor.equals("()L" + BLOCK + ";")) {
                            pending = true;
                        } else {
                            super.visitMethodInsn(opcode, owner, name, descriptor, isInterface);
                        }
                    }
                    @Override
                    public void visitEnd() {
                        if (pending) throw new IllegalStateException("Missing defaultBlockState");
                        super.visitEnd();
                    }
                };
            }
        }, 0);
        if (sites[0] != 1) throw new IllegalStateException("Expected one render site: " + sites[0]);
        Files.write(Path.of(args[1]), writer.toByteArray());
    }

    private static byte[] helper() {
        ClassWriter writer = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        writer.visit(V21, ACC_PUBLIC | ACC_FINAL, HELPER, null, PARENT, null);
        writer.visitField(ACC_PRIVATE | ACC_STATIC | ACC_FINAL, "INSTANCE", "L" + HELPER + ";", null, null).visitEnd();
        MethodVisitor init = writer.visitMethod(ACC_PRIVATE, "<init>", "()V", null, null);
        init.visitCode();
        init.visitVarInsn(ALOAD, 0);
        init.visitMethodInsn(INVOKESPECIAL, PARENT, "<init>", "()V", false);
        init.visitInsn(RETURN);
        init.visitMaxs(0, 0);
        init.visitEnd();
        MethodVisitor clinit = writer.visitMethod(ACC_STATIC, "<clinit>", "()V", null, null);
        clinit.visitCode();
        clinit.visitTypeInsn(NEW, HELPER);
        clinit.visitInsn(DUP);
        clinit.visitMethodInsn(INVOKESPECIAL, HELPER, "<init>", "()V", false);
        clinit.visitFieldInsn(PUTSTATIC, HELPER, "INSTANCE", "L" + HELPER + ";");
        clinit.visitInsn(RETURN);
        clinit.visitMaxs(0, 0);
        clinit.visitEnd();
        MethodVisitor resolve = writer.visitMethod(ACC_PUBLIC | ACC_STATIC, "resolve", RESOLVE, null, null);
        resolve.visitCode();
        resolve.visitFieldInsn(GETSTATIC, HELPER, "INSTANCE", "L" + HELPER + ";");
        resolve.visitVarInsn(ALOAD, 0);
        resolve.visitMethodInsn(INVOKEVIRTUAL, HELPER, "stateFor", RESOLVE, false);
        resolve.visitInsn(ARETURN);
        resolve.visitMaxs(0, 0);
        resolve.visitEnd();
        writer.visitEnd();
        return writer.toByteArray();
    }
}
