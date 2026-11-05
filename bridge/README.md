# AutoModpack 4.0.7 · D&C bridge dsh1

This is a modified LGPL-3.0 AutoModpack build for the Dreams & Crusades pilot. Original project https://github.com/Skidamek/AutoModpack/tree/v4.0.7 .

Build with Java 21+ and Python 3.12 using `python bridge/build.py`. The script downloads pinned upstream inputs, verifies SHA-256, applies the recorded source edits and compiles with target Java 21. Complete modified ModpackUpdater.java and the adapter source are embedded in the resulting JAR under META-INF/dsh-sources. Upstream licenses are retained.

Interactive updates always pass through AutoModpack's original cancel/confirm screen. Unverified-JAR acknowledgements remain. Clients must use updateSelectedModpackOnLaunch=false. A fixed project-owned public index supplies GitHub Releases URLs matched by the native object SHA-1 and size. Official platform URLs and original host fallback remain. The adapter does not mark project JARs as public-platform verified.

The workflow publishes experimental prereleases containing the modified bridge and a harmless resource probe. It does not publish a complete modpack or any player data. GitHub downloads and interactive update behavior must be verified before production deployment.
