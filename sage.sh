#!/bin/bash -x

export PATH="$PATH:/home/${USER}/miniforge3/envs/sage/bin"
export PATH="$PATH:/Users/${USER}/miniforge3/envs/sage/bin/"

clean() {
	rm -rf "${TEMP}"
	kill -s TERM "${TOP_PID}"
}

rm -rf ${TMPDIR}/tmp.*

SCRIPT_DIR=$(realpath "$(dirname "${BASH_SOURCE[0]}")")
LATEX_TEMP="/tmp/latex-temp"
TEMP="$(mktemp -d)"
DIRR="$(dirname "${1}")"
DIR="$(basename "${DIRR}")"
FILE="$(basename "${1}")"
FILENAME="$(basename -s .tex "${1}")"
export TOP_PID=$$

for pid in $(ps -ax | grep sage.sh | grep -v grep | awk '{ print $1 }'); do
	if [ ${pid} != $$ ]; then
		echo "Killing PID ${pid}"
		kill -9 ${pid}
	fi
done

killall pdflatex

cp -Lrv "${DIRR}" "${TEMP}"
pushd "${TEMP}/${DIR}"
latexindent "${TEMP}/${DIR}/${FILE}" > "${TEMP}/${DIR}/${FILE}.indent"
mv "${TEMP}/${DIR}/${FILE}.indent" "${TEMP}/${DIR}/${FILE}"

# Consolidate all \input files into the main file
if command -v latexpand >/dev/null 2>&1; then
	latexpand --keep-comments "${FILE}" > "${FILE}.tmp" && mv "${FILE}.tmp" "${FILE}"
fi

if [ -e "${TEMP}/${DIR}/.${FILE}_ee" ]; then
	TOOLTIP_ARG=0
	EXPAND_ARG=1
elif [ -e "${TEMP}/${DIR}/.${FILE}_eet" ]; then
	TOOLTIP_ARG=1
	EXPAND_ARG=1
elif [ -e "${TEMP}/${DIR}/.${FILE}_et" ]; then
	TOOLTIP_ARG=1
	EXPAND_ARG=0
else
	TOOLTIP_ARG=0
	EXPAND_ARG=0
fi

if [ ${TOOLTIP_ARG} != 0 ] || [ ${EXPAND_ARG} != 0 ]; then
	python3 "${SCRIPT_DIR}/preprocessing.py" ${EXPAND_ARG} ${TOOLTIP_ARG} "${TEMP}/${DIR}/${FILE}" "${TEMP}/${DIR}/${FILE}.f"
	mv "${TEMP}/${DIR}/${FILE}.f" "${TEMP}/${DIR}/${FILE}"
fi

pdflatex -shell-escape -halt-on-error "${TEMP}/${DIR}/${FILE}" || clean

[ -e "${TEMP}/${DIR}/${FILENAME}.sagetex.sage" ] && (sage "${TEMP}/${DIR}/${FILENAME}.sagetex.sage" || clean)

if [ -e "${TEMP}/${DIR}/${FILENAME}.sagetex.sout" ]; then
	python3 "${SCRIPT_DIR}/sagenum.py" "${TEMP}/${DIR}/${FILENAME}.sagetex.sout" > "${TEMP}/${DIR}/${FILENAME}.sagetex.soutf"
	mv "${TEMP}/${DIR}/${FILENAME}.sagetex.soutf" "${TEMP}/${DIR}/${FILENAME}.sagetex.sout"
fi

pdflatex -shell-escape -halt-on-error "${TEMP}/${DIR}/${FILE}" || clean
mkdir -p "${LATEX_TEMP}" && cp "${TEMP}/${DIR}/${FILENAME}.pdf" "${LATEX_TEMP}"
popd
rm -rf "${LATEX_TEMP}/last-built"
mkdir -p "${LATEX_TEMP}/last-built"
cp -Lr "${TEMP}/${DIR}" "${LATEX_TEMP}/last-built"
rm -rf "${TEMP}"

rm -f "${PIDFILE}"
