#!/bin/bash -x

# source /Users/nicolas/miniforge3/etc/profile.d/conda.sh &>/dev/null
# conda activate sage &>/dev/null

export PATH="$PATH:/Users/nicolas/miniforge3/envs/sage/bin/"

clean() {
	rm -rf "${TEMP}"
	kill -s TERM "${TOP_PID}"
}

rm -rf ${TMPDIR}/tmp.*

SCRIPT_DIR=$(realpath "$(dirname "${BASH_SOURCE[0]}")")
LATEX_TEMP="/tmp/latex-temp"
TEMP="$(mktemp -d)"
DIRR="$(dirname ""${1}"")"
DIR="$(basename ""${DIRR}"")"
FILE="$(basename ""${1}"")"
FILENAME="$(basename -s .tex ""${1}"")"
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

if [ -e "${TEMP}/${DIR}/.${FILE}_et" ]; then
	python3 "${SCRIPT_DIR}/preprocessing.py" "${TEMP}/${DIR}/${FILE}" "${TEMP}/${DIR}/${FILE}.f"
	mv "${TEMP}/${DIR}/${FILE}.f" "${TEMP}/${DIR}/${FILE}"
fi

pdflatex -halt-on-error "${TEMP}/${DIR}/${FILE}" || clean
[ -e "${TEMP}/${DIR}/${FILENAME}.sagetex.sage" ] && (sage "${TEMP}/${DIR}/${FILENAME}.sagetex.sage" || clean)
pdflatex -halt-on-error "${TEMP}/${DIR}/${FILE}" || clean
mkdir -p "${LATEX_TEMP}" && cp "${TEMP}/${DIR}/${FILENAME}.pdf" "${LATEX_TEMP}"
popd
rm -rf "${TEMP}"

rm -f "${PIDFILE}"
