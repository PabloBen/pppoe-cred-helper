#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Creado por FRIKIdelTO (https://www.frikidelto.com)
Este script fue desarrollado siguiendo el excelente tutorial de BocaDePez que publicó en:
https://bandaancha.eu/foros/sustituir-router-digi-fibra-router-1732730/2#r1lf3a
Todo el mérito es de él.

Muchas gracias a Manel (@VillaArtista en Telegram) por avisarme de dicho tutorial
y por aclararme dudas durante el desarrollo de este script.
"""

import argparse
import datetime as dt
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import netifaces

APP_NAME = "FRIKIpppoe"
VERSION = f"{APP_NAME} 20.11.06 by FRIKIdelTO.com"

# Colors
VERDE = "\33[92m"
AMARILLO = "\033[93m"
AZUL = "\033[96m"
MAGENTA = "\033[1m\033[95m"
GRIS = "\33[90m"
BLANCO = "\033[1m\033[97m"
ROJO = "\33[91m"

# Animated clock
RELOJ = ("🕐", "🕑", "🕒", "🕓", "🕔", "🕕", "🕖", "🕗", "🕘", "🕙", "🕚", "🕛")

# PPPoE server options
PPP_OPTIONS = """\
ms-dns 8.8.8.8 asyncmap 0
noauth
crtscts
lock
hide-password
modem
debug
proxyarp
lcp-echo-interval 10
lcp-echo-failure 2
noipx
plugin /etc/ppp/plugins/rp-pppoe.so
require-pap
ktune
nobsdcomp
noccp
novj
"""

OPERADORES = (
    ("DiGi", 20),
    ("Movistar/Tuenti/O2", 6),
    ("Vodafone/Lowi", 100),
    ("NEBA: Vodafone/Lowi", 24),
    ("Jazztel", 1074),
    ("MasMovil/PepePhone/Yoigo", 20),
    ("Orange/Amena", 832),
    ("Adamo", 603),
)

PAP_SECRETS_LINE = "\"Username\"\t*\t\"p4ssw0rd\"\t*\n"

INTERRUPTED = False


def cursor_arriba(n=1):
    print("\033[%sA" % (n + 1,))


def cuadro(texto):
    linea = "─"
    caracteres = len(texto) + 2
    print(AMARILLO + "┌" + linea * caracteres + "┐")
    print(AMARILLO + "│ " + BLANCO + texto + AMARILLO + " │")
    print(AMARILLO + "└" + linea * caracteres + "┘\n" + GRIS)


def animacion_reloj(texto, inicio):
    n_total = len(RELOJ)
    for n in range(n_total):
        segundos = (dt.datetime.now() - inicio).seconds
        mins, segs = divmod(segundos, 60)
        if segundos < 60:
            formato = "{:2d}      ".format(segs)
            print(BLANCO + "\033[K   " + RELOJ[n] + "️  " + AMARILLO + texto + "...... " + BLANCO + formato + GRIS)
        else:
            formato = "{:2d}:{:02d}".format(mins, segs)
            print(BLANCO + "\033[K   " + RELOJ[n] + "️  " + AMARILLO + texto + "... " + BLANCO + formato + GRIS)
        time.sleep(1 / n_total)
        cursor_arriba()


def mostrar_tiempo(empieza):
    segundos = (dt.datetime.now() - empieza).seconds
    if segundos <= 0:
        print(GRIS)
        return 0, 0

    color = ROJO if segundos >= 60 else VERDE
    minutos, segundos = divmod(segundos, 60)
    print(VERDE + "COMPLETADO" + color + " en ", end="")
    if minutos:
        print(BLANCO + str(minutos) + color + (" minuto" if minutos == 1 else " minutos"), end="")
        if segundos:
            print(color + " y ", end="")
    if segundos or not minutos:
        print(BLANCO + str(segundos) + color + (" segundo" if segundos == 1 else " segundos"), end="")
    print(GRIS)
    return minutos, segundos


def setup_logging(log_path):
    logger = logging.getLogger(APP_NAME)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s  %(message)s", "%d/%m/%Y_%H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def log_blank(logger):
    logger.handlers[0].stream.write("\n")
    logger.handlers[0].flush()


def clear_screen():
    print("\033c", end="")


def ensure_root():
    if os.geteuid() != 0:
        os.execvp("sudo", ["sudo", "python3", *sys.argv])


def run(cmd, check=True, capture=False):
    if capture:
        return subprocess.run(cmd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return subprocess.run(cmd, check=check)


def check_dependencies():
    missing = []
    for name in ("tshark", "pppoe-server", "ip"):
        if shutil.which(name) is None:
            missing.append(name)
    return missing


def kill_processes(logger):
    if shutil.which("pkill"):
        run(["pkill", "-f", "tshark"], check=False)
        run(["pkill", "-f", "pppoe-server"], check=False)
        logger.info("Procesos detenidos con pkill")
        return
    if shutil.which("killall"):
        run(["killall", "-q", "-w", "tshark"], check=False)
        run(["killall", "-q", "-w", "pppoe-server"], check=False)
        logger.info("Procesos detenidos con killall")


def write_ppp_options(logger):
    options_path = Path("/etc/ppp/options")
    if options_path.exists():
        backup_path = options_path.with_name("options.bak")
        try:
            backup_path.write_text(options_path.read_text(encoding="utf-8"), encoding="utf-8")
            logger.info("Copia de seguridad creada: %s", backup_path)
        except Exception:
            logger.info("No se ha podido crear copia de seguridad de %s", options_path)
    options_path.write_text(PPP_OPTIONS, encoding="utf-8")
    logger.info("Archivo options actualizado: %s", options_path)


def ensure_pap_secrets(logger):
    pap_path = Path("/etc/ppp/pap-secrets")
    contenido = pap_path.read_text(encoding="utf-8") if pap_path.exists() else ""
    if PAP_SECRETS_LINE not in contenido:
        pap_path.open("a", encoding="utf-8").write(PAP_SECRETS_LINE)
        logger.info("Entrada añadida a pap-secrets")
    else:
        logger.info("Entrada ya existente en pap-secrets")


def detect_interface(preferred=None):
    if preferred:
        return preferred

    candidates = [i for i in netifaces.interfaces() if i.startswith("eth") or i.startswith("en")]
    if not candidates:
        return ""
    if len(candidates) == 1:
        return candidates[0]

    print(azulestr("SE HAN ENCONTRADO VARIAS INTERFACES:"))
    for idx, name in enumerate(candidates, 1):
        print(BLANCO + f"[ {idx} ]  " + AMARILLO + name + GRIS)
    while True:
        try:
            opcion = int(input(AZUL + "Selecciona interfaz: " + BLANCO))
            if 1 <= opcion <= len(candidates):
                return candidates[opcion - 1]
        except KeyboardInterrupt:
            print()
            sys.exit(1)
        except Exception:
            pass
        print(ROJO + "   OPCIÓN NO VÁLIDA" + GRIS)


def select_vlan(vlan_arg=None):
    if vlan_arg is not None:
        return vlan_arg

    print()
    print(AZUL + "LISTA DE OPERADORAS FTTH:" + GRIS)
    print(AZUL + "════════════════════════" + GRIS)
    for n, (nombre, vlan) in enumerate(OPERADORES, 1):
        print(BLANCO + f"[ {n} ]  " + AMARILLO + nombre + MAGENTA + f"  (vlan: {vlan})" + GRIS)
    manual_index = len(OPERADORES) + 1
    print(BLANCO + f"[ {manual_index} ]  " + AMARILLO + "Introducir VLAN manualmente" + GRIS)
    print()

    while True:
        try:
            opcion = int(input(AZUL + "SELECCIONA TU OPERADOR: " + BLANCO))
            if 1 <= opcion <= manual_index:
                break
            print(ROJO + "   OPCIÓN NO VÁLIDA" + GRIS)
        except KeyboardInterrupt:
            print()
            sys.exit(1)
        except Exception:
            print(ROJO + "   OPCIÓN NO VÁLIDA: debes introducir un número" + GRIS)

    if opcion == manual_index:
        while True:
            try:
                return int(input(AZUL + "INTRODUCE la VLAN: " + BLANCO))
            except KeyboardInterrupt:
                print()
                sys.exit(1)
            except Exception:
                print(ROJO + "   VLAN NO VÁLIDA: debes introducir un número" + GRIS)
    return OPERADORES[opcion - 1][1]


def setup_vlan_interface(interfaz, vlan, logger):
    interfaz_vlan = f"{interfaz}.{vlan}"
    run(["ip", "link", "delete", interfaz_vlan], check=False)

    print(AZUL + f"\033[K   Creando interfaz virtual VLAN {vlan}: " + BLANCO + interfaz_vlan + GRIS)
    run(["ip", "link", "add", "link", interfaz, "name", interfaz_vlan, "type", "vlan", "id", str(vlan)])

    print(AZUL + f"\033[K   Asignando IP a {interfaz_vlan}" + GRIS)
    run(["ip", "addr", "flush", "dev", interfaz_vlan])
    run(["ip", "addr", "add", "10.0.0.1/16", "dev", interfaz_vlan])

    print(AZUL + f"\033[K   Levantando interfaz {interfaz_vlan}" + GRIS)
    run(["ip", "link", "set", interfaz_vlan, "up"])

    logger.info("Interfaz VLAN configurada: %s", interfaz_vlan)
    return interfaz_vlan


def start_pppoe_server(interfaz_vlan, logger):
    logger.info("Iniciando servidor PPPoE")
    return subprocess.Popen(
        ["pppoe-server", "-C", "ftth", "-I", interfaz_vlan, "-N", "256", "-O", "/etc/ppp/options"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def start_capture(interfaz_vlan, capture_path, logger):
    logger.info("Iniciando captura de tráfico con tshark")
    capture_file = capture_path.open("w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(
        ["tshark", "-i", interfaz_vlan, "-T", "text"],
        stdout=capture_file,
        stderr=subprocess.DEVNULL,
    )
    return proc, capture_file


def parse_credentials(line, user_re, pass_re):
    usuario = ""
    password = ""
    if "Authenticate-Request" in line:
        match_user = user_re.search(line)
        match_pass = pass_re.search(line)
        if match_user:
            usuario = match_user.group(1)
        if match_pass:
            password = match_pass.group(1)
    return usuario, password


def azulestr(texto):
    return AZUL + texto + GRIS


def handle_interrupt(signum, frame):
    global INTERRUPTED
    INTERRUPTED = True


def main():
    parser = argparse.ArgumentParser(description="Captura credenciales PPPoE usando un servidor falso.")
    parser.add_argument("--iface", help="Interfaz Ethernet (ej. eth0, enp3s0)")
    parser.add_argument("--vlan", type=int, help="VLAN a usar (omite para seleccionar)")
    parser.add_argument("--timeout", type=int, default=0, help="Timeout en segundos (0 = sin límite)")
    parser.add_argument("--no-clear", action="store_true", help="No limpiar pantalla")
    parser.add_argument("--skip-kb", action="store_true", help="No configurar teclado")
    args = parser.parse_args()

    ensure_root()

    work_dir = Path.home() / APP_NAME
    work_dir.mkdir(parents=True, exist_ok=True)
    log_path = work_dir / f"{APP_NAME}.log"
    logger = setup_logging(log_path)
    log_blank(logger)
    logger.info("INICIANDO el SCRIPT")

    if not args.no_clear:
        clear_screen()
    cuadro(VERSION)

    if not args.skip_kb and os.environ.get("DISPLAY") and shutil.which("setxkbmap"):
        run(["setxkbmap", "-layout", "es,es", "-model", "pc105"], check=False)

    missing = check_dependencies()
    if missing:
        print(ROJO + "Faltan dependencias: " + ", ".join(missing) + GRIS)
        print(AMARILLO + "Ejecuta primero: sudo ./install.sh" + GRIS)
        logger.info("Dependencias faltantes: %s", ", ".join(missing))
        sys.exit(1)

    kill_processes(logger)

    print(AZUL + "\033[K   Configurando servidor PPPoE (options)" + GRIS)
    try:
        write_ppp_options(logger)
    except Exception as exc:
        print(ROJO + "\033[K      ERROR al escribir /etc/ppp/options" + GRIS)
        logger.info("ERROR al escribir /etc/ppp/options: %s", exc)
        sys.exit(1)

    print(AZUL + "\033[K   Configurando servidor PPPoE (pap-secrets)" + GRIS)
    try:
        ensure_pap_secrets(logger)
    except Exception as exc:
        print(ROJO + "\033[K      ERROR al escribir /etc/ppp/pap-secrets" + GRIS)
        logger.info("ERROR al escribir /etc/ppp/pap-secrets: %s", exc)
        sys.exit(1)

    print(AZUL + "\033[K   Buscando interfaz Ethernet" + GRIS)
    interfaz = detect_interface(args.iface)
    if not interfaz:
        print(ROJO + "\033[K      ERROR: No se ha podido detectar la interfaz Ethernet" + GRIS)
        logger.info("No se ha podido determinar la interfaz Ethernet")
        sys.exit(1)
    print(VERDE + "\033[K      Encontrada: " + BLANCO + interfaz + GRIS)
    logger.info("Interfaz ethernet seleccionada: %s", interfaz)

    vlan = select_vlan(args.vlan)
    logger.info("VLAN seleccionada: %s", vlan)

    try:
        interfaz_vlan = setup_vlan_interface(interfaz, vlan, logger)
    except Exception as exc:
        print(ROJO + "\033[K      ERROR al configurar la interfaz VLAN" + GRIS)
        logger.info("ERROR al configurar la interfaz VLAN: %s", exc)
        sys.exit(1)

    print(GRIS)
    print(azulestr("YA ESTÁ TODO PREPARADO PARA CAPTURAR EL TRÁFICO DEL ROUTER."))
    print(azulestr("A PARTIR DE ESTE PUNTO YA NO ES NECESARIO ESTAR CONECTADO A INTERNET"))
    print(azulestr("ASÍ QUE, SI QUIERES O LO NECESITAS PARA CONTINUAR, PUEDES DESCONECTARTE."))
    print(azulestr("CONECTA UN CABLE DE RED DESDE EL ORDENADOR AL PUERTO WAN DEL ROUTER Y ENCIÉNDELO."))
    print(GRIS)
    input(BLANCO + "\033[KPulsa ENTER cuando estés listo... " + GRIS)
    cursor_arriba()

    kill_processes(logger)

    print(AZUL + "\033[K   Iniciando servidor PPPoE" + GRIS)
    try:
        pppoe_proc = start_pppoe_server(interfaz_vlan, logger)
    except Exception as exc:
        print(ROJO + "\033[K      ERROR al iniciar pppoe-server" + GRIS)
        logger.info("ERROR al iniciar pppoe-server: %s", exc)
        sys.exit(1)
    time.sleep(1)

    print(AZUL + "\033[K   Iniciando captura de tráfico de red" + GRIS)
    captura_path = work_dir / "captura.txt"
    try:
        tshark_proc, capture_file = start_capture(interfaz_vlan, captura_path, logger)
    except Exception as exc:
        print(ROJO + "\033[K      ERROR al iniciar tshark" + GRIS)
        logger.info("ERROR al iniciar tshark: %s", exc)
        sys.exit(1)

    print()
    usuario = ""
    password = ""
    inicio = dt.datetime.now()
    pos = 0

    user_re = re.compile(r"Peer-ID='([@A-Za-z0-9_\./\\-]*)'")
    pass_re = re.compile(r"Password='([@A-Za-z0-9_\./\\-]*)'")

    while not (usuario and password):
        if INTERRUPTED:
            break

        animacion_reloj("BUSCANDO...", inicio)

        with captura_path.open("r", encoding="utf-8", errors="replace") as archivo:
            archivo.seek(pos)
            for linea in archivo:
                u, p = parse_credentials(linea, user_re, pass_re)
                if u:
                    usuario = u
                if p:
                    password = p
                if usuario and password:
                    break
            pos = archivo.tell()

        if args.timeout and (dt.datetime.now() - inicio).seconds >= args.timeout:
            break

    if usuario and password:
        print("\033[K")
        print(AMARILLO + "\033[K¡¡¡ CREDENCIALES PPPoE ENCONTRADAS !!!" + GRIS)
        print("\033[K")
        print(VERDE + "\033[KUsuario.....: " + BLANCO + str(usuario) + GRIS)
        print(VERDE + "\033[KContraseña..: " + BLANCO + str(password) + GRIS)
        print("\033[K")
        mostrar_tiempo(inicio)
        logger.info("Credenciales encontradas")
    else:
        print(ROJO + "\033[KNo se han encontrado credenciales." + GRIS)
        logger.info("No se han encontrado credenciales")

    capture_file.close()
    print(GRIS + "\033[KDeteniendo captura" + GRIS)
    kill_processes(logger)
    if pppoe_proc.poll() is None:
        pppoe_proc.terminate()
    if tshark_proc.poll() is None:
        tshark_proc.terminate()

    print(AZUL + "\033[KCaptura detenida" + GRIS)

    if INTERRUPTED:
        print(ROJO + "\033[KInterrumpido por el usuario" + GRIS)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_interrupt)
    signal.signal(signal.SIGTERM, handle_interrupt)
    main()
