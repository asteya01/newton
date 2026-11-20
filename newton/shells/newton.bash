# ─────────────────────────────────────────────────────────────────────────────
#  Newton for bash — Think it. Tab it. Done.
#  Load with:  eval "$(newton init bash)"   (near the end of ~/.bashrc)
#
#    Tab        plain English → command   (normal completion otherwise)
#    Tab again  cycle through alternative commands
#    Shift+Tab  put your original words back
#    Alt+N      force Newton on the current line
#    # prefix   "# anything" always goes to Newton
#  Requires bash 4+ (macOS ships 3.2: `brew install bash`).
# ─────────────────────────────────────────────────────────────────────────────
if [[ $- == *i* && -z "$_NEWTON_LOADED" && ${BASH_VERSINFO[0]:-0} -ge 4 ]]; then
_NEWTON_LOADED=1
export NEWTON_SHELL_INTEGRATION=bash

_newton_alts=()
_newton_idx=0
_newton_last=""
_newton_orig=""
_newton_tab_fallback="$(bind -p 2>/dev/null | sed -n 's/^"\\C-i": //p' | head -n1)"
case "$_newton_tab_fallback" in ""|*newton*|self-insert) _newton_tab_fallback=complete ;; esac

_newton_english=" the a an all every that which from into in on of for with my me than bigger larger smaller older newer files folder folders directory directories this these those is are using named called containing recursively everything each current last and or how what show list to by at it its you please can i want not only any new old big large small biggest largest first top count number size sizes bytes lines line name names extension type modified created today yesterday hours days minutes ago port process processes running listening free space disk memory usage over under between per out up down again then so was be do does display get give print find where who when why inside outside text content contents whose has have had "
_newton_subcmds=" suggest explain setup init doctor history config help plan resume plans status prompt ask chat fix commit update uninstall "

_newton_is_natural() {
  local line="${1# }" w hits=0
  [[ "$line" == '#'* ]] && return 0
  [[ "${NEWTON_TRIGGER:-smart}" == prefix ]] && return 1
  [[ "$line" == *[\|\<\>\&\;\$\`\=\\\"\{\}]* ]] && return 1
  local -a words
  read -r -a words <<< "$line"
  (( ${#words[@]} >= 3 )) || return 1
  for w in "${words[@]}"; do [[ "$w" == -* ]] && return 1; done
  if [[ "${words[0]}" == newton ]]; then
    [[ "$_newton_subcmds" == *" ${words[1]} "* ]] && return 1
    return 0
  fi
  type -t -- "${words[0]}" >/dev/null 2>&1 || return 0
  for w in "${words[@]:1}"; do
    [[ "$_newton_english" == *" ${w,,} "* ]] && hits=$((hits + 1))
  done
  (( hits >= 2 )) && return 0
  (( hits >= 1 && ${#words[@]} >= 4 )) || return 1
  [[ "$line" == *[/.~\*\?@:]* ]] && return 1
  return 0
}

_newton_say() { printf '\r\033[2K\033[38;5;245m%s\033[0m\n' "$*" >&2; }

_newton_translate() {
  local desc="$READLINE_LINE" out line cmd="" note="" warn="" errmsg=""
  local -a alts=()
  printf '\r\033[2K\033[38;5;245m  ◌ newton is thinking…\033[0m' >&2
  local ask="$desc"; [[ "$ask" == "newton "* ]] && ask="${ask#newton }"
  out="$(command newton suggest --porcelain --shell bash -- "$ask" 2>/dev/null)"
  while IFS= read -r line; do
    case "${line%%$'\t'*}" in
      cmd)  cmd="${line#*$'\t'}" ;;
      alt)  alts+=("${line#*$'\t'}") ;;
      note) note="${line#*$'\t'}" ;;
      warn) warn="${line#*$'\t'}" ;;
      err)  errmsg="${line#*$'\t'}" ;;
    esac
  done <<< "$out"
  if [[ -z "$cmd" ]]; then
    _newton_say "  ✗ newton: ${errmsg:-no answer (try \`newton doctor\`)}"
    return
  fi
  _newton_orig="$desc"
  _newton_alts=("$cmd" "${alts[@]}")
  _newton_idx=0
  READLINE_LINE="$cmd"; READLINE_POINT=${#READLINE_LINE}; _newton_last="$cmd"
  local msg="  ❯ ${note:-ready — review it, then press Enter}"
  (( ${#alts[@]} )) && msg+="   ·  ⇥ ${#alts[@]} more"
  msg+="   ·  ⇧⇥ undo"
  _newton_say "$msg"
  [[ -n "$warn" ]] && _newton_say "  ▲ careful: $warn"
}

# Tab is bound to a two-key macro: the first key runs this function, which then
# rebinds the second key to either a no-op (Newton handled it) or normal completion.
_newton_tab() {
  if [[ -n "$_newton_last" && "$READLINE_LINE" == "$_newton_last" && ${#_newton_alts[@]} -gt 1 ]]; then
    _newton_idx=$(( (_newton_idx + 1) % ${#_newton_alts[@]} ))
    READLINE_LINE="${_newton_alts[_newton_idx]}"; READLINE_POINT=${#READLINE_LINE}; _newton_last="$READLINE_LINE"
    bind '"\C-x\C-n2": redraw-current-line'
  elif _newton_is_natural "$READLINE_LINE"; then
    _newton_translate
    bind '"\C-x\C-n2": redraw-current-line'
  else
    bind "\"\\C-x\\C-n2\": $_newton_tab_fallback"
  fi
}

_newton_revert() {
  if [[ -n "$_newton_last" && "$READLINE_LINE" == "$_newton_last" ]]; then
    READLINE_LINE="$_newton_orig"; READLINE_POINT=${#READLINE_LINE}; _newton_last=""
  fi
}

_newton_force() { _newton_translate; }

bind -x '"\C-x\C-n1": _newton_tab'
bind '"\C-x\C-n2": complete'
bind '"\t": "\C-x\C-n1\C-x\C-n2"'
bind -x '"\e[Z": _newton_revert'
bind -x '"\en": _newton_force'

# ── last-command memory for `newton fix` (written to a private file, never exported into child processes) ──
_newton_last_file="${XDG_CACHE_HOME:-$HOME/.cache}/newton/last-$$"
[[ -d "${_newton_last_file%/*}" ]] || mkdir -m 700 -p "${_newton_last_file%/*}" 2>/dev/null
export NEWTON_LAST_FILE="$_newton_last_file"
_newton_hn=""
_newton_record() {
  local st=$?
  [[ "$HISTCMD" == "$_newton_hn" ]] && return $st      # empty Enter / no new command
  _newton_hn="$HISTCMD"
  local cmd
  cmd="$(HISTTIMEFORMAT= builtin history 1)"
  [[ $cmd =~ ^[[:space:]]*[0-9]+[[:space:]]+(.*)$ ]] && cmd="${BASH_REMATCH[1]}"
  [[ "$cmd" == newton || "$cmd" == newton\ * ]] && return $st
  printf '%s\n%s\n' "$st" "$cmd" > "$_newton_last_file" 2>/dev/null
  return $st
}
if [[ "$(declare -p PROMPT_COMMAND 2>/dev/null)" == "declare -a"* ]]; then
  PROMPT_COMMAND=(_newton_record "${PROMPT_COMMAND[@]}")
else
  PROMPT_COMMAND="_newton_record${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
fi
fi
