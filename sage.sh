#!/bin/bash -x

clean() {
	rm -rf "${TEMP}"
	kill -s TERM "${TOP_PID}"
}

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
pdflatex -halt-on-error "${TEMP}/${DIR}/${FILE}" || clean
[ -e "${TEMP}/${DIR}/${FILENAME}.sagetex.sage" ] && (sage "${TEMP}/${DIR}/${FILENAME}.sagetex.sage" || clean)
pdflatex -halt-on-error "${TEMP}/${DIR}/${FILE}" || clean
mkdir -p "${LATEX_TEMP}" && cp "${TEMP}/${DIR}/${FILENAME}.pdf" "${LATEX_TEMP}"
popd
rm -rf "${TEMP}"

rm -f "${PIDFILE}"
