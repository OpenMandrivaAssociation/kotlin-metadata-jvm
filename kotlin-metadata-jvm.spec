Name:		kotlin-metadata-jvm
Version:	2.4.21
Release:	1
Summary:	Kotlin JVM metadata library
Group:		Development/Java
License:	Apache-2.0 AND BSD-3-Clause
URL:		https://github.com/JetBrains/kotlin
# Kotlin tag v2.4.21. The published kotlin-metadata-jvm jar is the
# kotlinx-metadata JVM module with core/metadata, core/metadata.jvm,
# and protobuf lite shaded in. Square-bracket destructuring from the
# 2.3 language line is rewritten to the position-based form that
# kotlinc 2.0.21 accepts. SinceKotlin 2.2 is dropped from the
# context-parameters opt-in annotation in this same tag so that
# compiler can resolve it. Embedded org.jetbrains.kotlin packages are
# rewritten to kotlin.metadata.internal, matching the upstream relocate,
# so the jar can sit beside kotlin-compiler-embeddable.
Source0:	kotlin-metadata-jvm-%{version}.tar.gz
Source1:	protobuf-2.6.1.tar.gz
Patch0:	kotlin-metadata-jvm-kotlin20-syntax.patch

BuildArch:	noarch
BuildRequires:	java-21-openjdk-devel
BuildRequires:	kotlin
BuildRequires:	sysjar
BuildRequires:	javapackages-filesystem
BuildRequires:	mvn(org.jetbrains:annotations)

%description
org.jetbrains.kotlin:kotlin-metadata-jvm %{version}. KotlinClassMetadata
reads the Metadata annotation of a class file. The sources are compiled
with javac and the installed kotlinc. Protobuf 2.6.1 lite is compiled
from source and relocated into the jar.

%prep
%autosetup -n kotlin-metadata-jvm-%{version} -p1 -a 1
find . -type f \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -print > binaries.list
find . -type d -name '*.jar' -print >> binaries.list
if [ -s binaries.list ]; then
	cat binaries.list
	exit 1
fi
grep -F -q 'val (packageFqNameSegments, relativeClassNameSegments)' \
	core/metadata/src/org/jetbrains/kotlin/metadata/deserialization/NameResolverImpl.kt
sed -i '/@SinceKotlin("2.2")/d' \
	libraries/stdlib/src/kotlin/contextParameters/ExperimentalContextParameters.kt
if grep -F -q '@SinceKotlin("2.2")' \
	libraries/stdlib/src/kotlin/contextParameters/ExperimentalContextParameters.kt; then
	exit 1
fi
find core libraries/kotlinx-metadata -type f \( -name '*.java' -o -name '*.kt' \) -print0 \
	| xargs -0 sed -i 's/org\.jetbrains\.kotlin/kotlin.metadata.internal/g'
if grep -R -F -q 'org.jetbrains.kotlin' core libraries/kotlinx-metadata --include='*.java' --include='*.kt'; then
	grep -R -n -F 'org.jetbrains.kotlin' core libraries/kotlinx-metadata --include='*.java' --include='*.kt'
	exit 1
fi
pb=protobuf-2.6.1/java/src/main/java/com/google/protobuf
cp -f dependencies/protobuf/protobuf-patches/src/main/java/com/google/protobuf/CodedInputStream.java \
	"$pb/CodedInputStream.java"
: > lite.list
for f in \
	AbstractMessageLite ByteString CodedInputStream CodedOutputStream \
	ExtensionRegistryLite FieldSet GeneratedMessageLite Internal \
	InvalidProtocolBufferException LazyStringArrayList LazyStringList \
	MessageLite MessageLiteOrBuilder SmallSortedMap \
	UninitializedMessageException UnmodifiableLazyStringList WireFormat \
	Parser AbstractParser BoundedByteString LiteralByteString \
	RopeByteString Utf8 LazyField LazyFieldLite ProtocolStringList
do
	sed -i 's/com\.google\.protobuf/kotlin.metadata.internal.protobuf/g' "$pb/$f.java"
	echo "$pb/$f.java" >> lite.list
done
test "$(wc -l < lite.list)" -eq 26
grep -F -q 'package kotlin.metadata.internal.metadata;' \
	core/metadata/src/org/jetbrains/kotlin/metadata/ProtoBuf.java
grep -F -q 'package kotlin.metadata.internal.protobuf;' \
	"$pb/GeneratedMessageLite.java"

%build
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-21-openjdk
export PATH="$JAVA_HOME/bin:/usr/bin:/bin"
CPANN=%{_javadir}/org.jetbrains.annotations.jar
CPSTD=%{_javadir}/kotlin-stdlib.jar
test -s "$CPANN"
test -s "$CPSTD"
mkdir -p classes
javac --release 8 -Xlint:-options -encoding UTF-8 -d classes @lite.list
find core/metadata/src core/metadata.jvm/src -name '*.java' ! -name 'BitEncoding.java' > internal-java.list
javac --release 8 -Xlint:-options -encoding UTF-8 -cp "classes:$CPANN:$CPSTD" -d classes @internal-java.list
find core/metadata/src core/metadata.jvm/src -name '*.kt' > internal-kt.list
kotlinc -J-Xmx2g -jvm-target 1.8 -language-version 2.0 -Xallow-kotlin-package \
	-cp "classes:$CPANN:$CPSTD" -d classes @internal-kt.list \
	core/metadata.jvm/src/org/jetbrains/kotlin/metadata/jvm/deserialization/BitEncoding.java
javac --release 8 -Xlint:-options -encoding UTF-8 -cp "classes:$CPANN:$CPSTD" -d classes \
	core/metadata.jvm/src/org/jetbrains/kotlin/metadata/jvm/deserialization/BitEncoding.java
find libraries/kotlinx-metadata/src libraries/kotlinx-metadata/jvm/src -name '*.kt' > public-kt.list
echo libraries/stdlib/src/kotlin/contextParameters/ExperimentalContextParameters.kt >> public-kt.list
kotlinc -J-Xmx2g -jvm-target 1.8 -language-version 2.0 \
	-Xallow-kotlin-package -Xexplicit-api=strict \
	-cp "classes:$CPANN:$CPSTD:/usr/share/java/kotlin-stdlib-jdk7.jar:/usr/share/java/kotlin-stdlib-jdk8.jar" \
	-d classes @public-kt.list
javac --release 8 -Xlint:-options -encoding UTF-8 -cp "classes:$CPANN:$CPSTD" -d classes \
	libraries/kotlinx-metadata/jvm/src/kotlin/metadata/jvm/KotlinClassHeader.java
mkdir -p classes/META-INF/services
cp -f libraries/kotlinx-metadata/jvm/resources/META-INF/services/kotlin.metadata.internal.extensions.MetadataExtensions \
	classes/META-INF/services/kotlin.metadata.internal.extensions.MetadataExtensions
test -s classes/kotlin/metadata/jvm/KotlinClassMetadata.class
test -s classes/kotlin/metadata/internal/metadata/ProtoBuf.class
test -s classes/kotlin/metadata/internal/protobuf/GeneratedMessageLite.class
test -s classes/kotlin/metadata/jvm/KotlinClassHeader.class
test -s classes/kotlin/metadata/jvm/internal/JvmMetadataExtensions.class
if find classes -path '*/org/jetbrains/kotlin/metadata/*' -name '*.class' | grep -q .; then
	exit 1
fi
javap -v -classpath classes kotlin.metadata.jvm.KotlinClassMetadata | grep -F -q 'major version: 52'
printf '%s\n' 'Manifest-Version: 1.0' 'Automatic-Module-Name: kotlin.metadata.jvm' > manifest.mf
jar cfm kotlin-metadata-jvm.jar manifest.mf -C classes .
jar i kotlin-metadata-jvm.jar
jar tf kotlin-metadata-jvm.jar | grep -F -q 'kotlin/metadata/jvm/KotlinClassMetadata.class'
jar tf kotlin-metadata-jvm.jar | grep -F -q 'kotlin/metadata/internal/metadata/ProtoBuf.class'
jar tf kotlin-metadata-jvm.jar | grep -F -q 'META-INF/services/kotlin.metadata.internal.extensions.MetadataExtensions'
if jar tf kotlin-metadata-jvm.jar | grep -F -q 'org/jetbrains/kotlin/metadata/ProtoBuf.class'; then
	exit 1
fi
if jar tf kotlin-metadata-jvm.jar | grep -F -q 'com/google/protobuf/'; then
	exit 1
fi
desc=$(jar --describe-module --file kotlin-metadata-jvm.jar)
printf '%s\n' "$desc"
if printf '%s\n' "$desc" | grep -F -q 'Unable'; then
	exit 1
fi
printf '%s\n' "$desc" | grep -F -q 'kotlin.metadata.jvm'

cat > kotlin-metadata-jvm.pom << END
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.jetbrains.kotlin</groupId>
  <artifactId>kotlin-metadata-jvm</artifactId>
  <version>%{version}</version>
  <name>kotlin-metadata-jvm</name>
  <description>Kotlin JVM metadata manipulation library.</description>
  <url>https://github.com/JetBrains/kotlin</url>
  <licenses>
    <license>
      <name>Apache-2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>org.jetbrains.kotlin</groupId>
      <artifactId>kotlin-stdlib</artifactId>
      <version>2.0.21</version>
    </dependency>
    <dependency>
      <groupId>org.jetbrains</groupId>
      <artifactId>annotations</artifactId>
      <version>24.0.1</version>
      <scope>provided</scope>
    </dependency>
  </dependencies>
</project>
END

%install
set -eo pipefail
sysjar install --buildroot %{buildroot} \
	--artifact kotlin-metadata-jvm.pom:kotlin-metadata-jvm.jar \
	--file-name kotlin-metadata-jvm \
	--filelist .mfiles
idx="%{buildroot}/usr/share/sysjar/index/org.jetbrains.kotlin/kotlin-metadata-jvm.sysjar"
test -s "$idx"
grep -F -q '"version": "%{version}"' "$idx"
grep -F -q '"artifactId": "kotlin-metadata-jvm"' "$idx"
test -s %{buildroot}%{_javadir}/kotlin-metadata-jvm.jar

%check
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-21-openjdk
export PATH="$JAVA_HOME/bin:/usr/bin:/bin"
JAR=%{buildroot}%{_javadir}/kotlin-metadata-jvm.jar
test -s "$JAR"
test -s /usr/share/java/kotlin-compiler-embeddable.jar
STDLIB=/usr/share/java/kotlin-stdlib.jar:/usr/share/java/kotlin-stdlib-jdk7.jar:/usr/share/java/kotlin-stdlib-jdk8.jar
mkdir -p check
cat > check/Sample.kt << 'EOF'
class Sample
EOF
cat > check/Check.kt << 'EOF'
import kotlin.metadata.jvm.KotlinClassMetadata

fun main() {
    val md = Sample::class.java.getAnnotation(Metadata::class.java)
        ?: error("no kotlin metadata")
    val parsed = KotlinClassMetadata.readStrict(md)
    val cls = parsed as KotlinClassMetadata.Class
    if (cls.kmClass.name != "Sample") {
        error(cls.kmClass.name)
    }
    println("kotlin_metadata_jvm_ok " + cls.kmClass.name)
}
EOF
kotlinc -J-Xmx1g -jvm-target 1.8 -language-version 2.0 -d check/sample check/Sample.kt
kotlinc -J-Xmx1g -jvm-target 1.8 -language-version 2.0 \
	-cp "$JAR:$STDLIB:check/sample" -d check/out check/Check.kt
java -cp "/usr/share/java/kotlin-compiler-embeddable.jar:check/out:check/sample:$JAR:$STDLIB" CheckKt > check/out.txt
cat check/out.txt
grep -F -qx 'kotlin_metadata_jvm_ok Sample' check/out.txt

%files -f .mfiles
%license license/LICENSE.txt
%license protobuf-2.6.1/LICENSE
%doc license/NOTICE.txt
