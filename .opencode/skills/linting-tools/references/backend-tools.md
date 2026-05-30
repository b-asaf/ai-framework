# Backend Linting Tools

## SonarQube (frontend and backend)
**Detection:** `sonar-project.properties`, `sonar` script in `package.json`, `sonar-maven-plugin` in `pom.xml`, or `sonar` Gradle task
```bash
npm run sonar          # frontend
mvn sonar:sonar        # Maven
./gradlew sonar        # Gradle
```
Requires `SONAR_HOST_URL` and `SONAR_TOKEN`. If server unreachable, report and skip.

## Checkstyle (Java)
**Detection:** `checkstyle*.xml` or `maven-checkstyle-plugin` in `pom.xml`
```bash
./mvnw checkstyle:check
```

## SpotBugs (Java)
**Detection:** `spotbugs-maven-plugin` in `pom.xml`
```bash
./mvnw spotbugs:check
```
Focus on HIGH and MEDIUM priority findings.

## PMD (Java)
**Detection:** `maven-pmd-plugin` in `pom.xml`
```bash
./mvnw pmd:check
```

## ktlint (Kotlin)
**Detection:** `ktlint` task in Gradle config
```bash
./gradlew ktlintCheck      # report
./gradlew ktlintFormat     # auto-fix
```

## Detekt (Kotlin)
**Detection:** `detekt` plugin in Gradle config
```bash
./gradlew detekt
```

## Klocwork (C, C++, C#, Java)
**Detection:** `.kwlp` project file, `kwinject` CLI, or Klocwork step in CI
```bash
kwinject make
kwbuildproject --url http://<server>/<project> compile_commands.json
```
Requires a running Klocwork server. If unreachable, report and skip.
Relevant for C/C++/C# — lower value on pure JVM projects.