# Jenkins + Docker CLI + Python — pipeline'ın hem test (python) hem imaj build
# (docker) yapabilmesi için standart Jenkins imajını genişletir.
FROM jenkins/jenkins:lts-jdk17

# apt kurulumları root gerektirir; sonra jenkins kullanıcısına döneceğiz.
USER root

# 1) Docker CLI + compose eklentisi (host soketini kullanmak için — DooD).
#    Docker'ın resmi apt deposunu ekleyip yalnızca CLI'yi kuruyoruz (daemon değil).
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
 && install -m 0755 -d /etc/apt/keyrings \
 && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
 && chmod a+r /etc/apt/keyrings/docker.asc \
 && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" \
      > /etc/apt/sources.list.d/docker.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
 && rm -rf /var/lib/apt/lists/*

# 2) Python + venv + derleme araçları (testleri çalıştırmak için).
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv python3-pip build-essential \
 && rm -rf /var/lib/apt/lists/*

USER jenkins
