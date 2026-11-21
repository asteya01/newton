# ─────────────────────────────────────────────────────────────────────────────
#  Newton for zsh — Think it. Tab it. Done.
#  Load with:  eval "$(newton init zsh)"   (put it near the END of ~/.zshrc,
#  after oh-my-zsh / other plugins, so Newton can hand Tab back to them)
#
#    Tab        plain English → command   (normal completion otherwise)
#    Tab again  cycle through alternative commands
#    Shift+Tab  put your original words back
#    Alt+N      force Newton (or press Esc then N) on the current line, whatever it looks like
#    # prefix   "# anything" always goes to Newton
# ─────────────────────────────────────────────────────────────────────────────
if [[ -z "$_NEWTON_LOADED" ]]; then
typeset -g _NEWTON_LOADED=1
export NEWTON_SHELL_INTEGRATION=zsh

typeset -ga _newton_alts
typeset -gi _newton_idx=0
typeset -g _newton_last="" _newton_orig=""
typeset -g _newton_tab_fallback="${$(bindkey '^I' 2>/dev/null)##* }"
typeset -g _newton_stab_fallback="${$(bindkey '^[[Z' 2>/dev/null)##* }"
[[ -z "$_newton_tab_fallback" || "$_newton_tab_fallback" == _newton_* || "$_newton_tab_fallback" == undefined-key ]] && _newton_tab_fallback=expand-or-complete
[[ -z "$_newton_stab_fallback" || "$_newton_stab_fallback" == _newton_* || "$_newton_stab_fallback" == undefined-key ]] && _newton_stab_fallback=reverse-menu-complete

# Words that show up in plain-English requests but rarely as shell arguments.
typeset -ga _newton_english=(the a an all every that which from into in on of for with my me than
  bigger larger smaller older newer files folder folders directory directories this these those is are
  using named called containing recursively everything each current last and or how what show list
  to by at it its you please can i want not only any new old big large small biggest largest first top count number size sizes bytes lines line name names extension type modified created today yesterday hours days minutes ago port process processes running listening free space disk memory usage over under between per out up down again then so was be do does display get give print find where who when why inside outside text content contents whose has have had)
typeset -g _newton_subcmds=" suggest explain setup init doctor history config help plan resume plans status prompt ask chat fix commit agent update uninstall "

_newton_is_natural() {
  emulate -L zsh
  local line="${1## }"
  [[ "$line" == '#'* ]] && return 0
  [[ "${NEWTON_TRIGGER:-smart}" == prefix ]] && return 1
  # Real shell syntax means you're writing a command, not a sentence.
  [[ "$line" == *[\|\<\>\&\;\$\`\=\\\"\{\}]* ]] && return 1
  local -a words=(${=line})
  (( ${#words} >= 3 )) || return 1
  local w
  for w in $words; do [[ "$w" == -* ]] && return 1; done
  # `newton find big files` (the documented shorthand): anything that isn't a subcommand is a sentence.
  if [[ "${words[1]}" == newton ]]; then
    [[ "$_newton_subcmds" == *" ${words[2]} "* ]] && return 1
    return 0
  fi
  # First word isn't a command/alias/function → a sentence.
  whence -- "${words[1]}" >/dev/null 2>&1 || return 0
  # First word *is* a command ("find", "kill", "git"…) → look for English.
  local -i hits=0
  for w in ${words[2,-1]}; do (( ${_newton_english[(Ie)${w:l}]} )) && (( hits++ )); done
  (( hits >= 2 )) && return 0
  # Four or more words with one English word and nothing path-like is still a sentence.
  (( hits >= 1 && ${#words} >= 4 )) || return 1
  [[ "$line" == *[/.~\*\?@:]* ]] && return 1
  return 0
}

_newton_translate() {
  emulate -L zsh
  local desc="$BUFFER" out line cmd note warn errmsg
  local -a alts
  zle -M "  ◌ newton is thinking…"
  zle -R
  local ask="$desc"; [[ "$ask" == "newton "* ]] && ask="${ask#newton }"
  out="$(command newton suggest --porcelain --shell zsh -- "$ask" 2>/dev/null)"
  for line in "${(@f)out}"; do
    case "${line%%$'\t'*}" in
      cmd)  cmd="${line#*$'\t'}" ;;
      alt)  alts+=("${line#*$'\t'}") ;;
      note) note="${line#*$'\t'}" ;;
      warn) warn="${line#*$'\t'}" ;;
      err)  errmsg="${line#*$'\t'}" ;;
    esac
  done
  if [[ -z "$cmd" ]]; then
    zle -M "  ✗ newton: ${errmsg:-no answer (is \`newton\` on your PATH? try \`newton doctor\`)}"
    return 1
  fi
  _newton_orig="$desc"
  _newton_alts=("$cmd" "${alts[@]}")
  _newton_idx=1
  BUFFER="$cmd"; CURSOR=${#BUFFER}; _newton_last="$BUFFER"
  local msg="  ❯ ${note:-ready — review it, then press Enter}"
  (( ${#alts} )) && msg+="   ·  ⇥ ${#alts} more"
  msg+="   ·  ⇧⇥ undo"
  [[ -n "$warn" ]] && msg+=$'\n'"  ▲ careful: $warn"
  zle -M "$msg"
}

_newton_tab() {
  emulate -L zsh
  if [[ -n "$_newton_last" && "$BUFFER" == "$_newton_last" && ${#_newton_alts} -gt 1 ]]; then
    (( _newton_idx = _newton_idx % ${#_newton_alts} + 1 ))
    BUFFER="${_newton_alts[_newton_idx]}"; CURSOR=${#BUFFER}; _newton_last="$BUFFER"
    zle -M "  ❯ option $_newton_idx of ${#_newton_alts}   ·  ⇥ next   ·  ⇧⇥ undo"
    return
  fi
  if _newton_is_natural "$BUFFER"; then
    _newton_translate
  else
    zle "$_newton_tab_fallback"
  fi
}

_newton_force() { _newton_translate; }

_newton_revert() {
  emulate -L zsh
  if [[ -n "$_newton_last" && "$BUFFER" == "$_newton_last" ]]; then
    BUFFER="$_newton_orig"; CURSOR=${#BUFFER}; _newton_last=""
    zle -M "  ↺ back to your words"
  else
    zle "$_newton_stab_fallback"
  fi
}

zle -N _newton_tab
zle -N _newton_force
zle -N _newton_revert
for _newton_km in emacs viins; do
  bindkey -M $_newton_km '^I' _newton_tab
  bindkey -M $_newton_km '^[[Z' _newton_revert
  bindkey -M $_newton_km '^[n' _newton_force
done
unset _newton_km

# ── last-command memory for `newton fix` (written to a private file, never exported into child processes) ──
typeset -g _newton_cmd="" _newton_last_file="${XDG_CACHE_HOME:-$HOME/.cache}/newton/last-$$"
[[ -d "${_newton_last_file:h}" ]] || mkdir -m 700 -p "${_newton_last_file:h}" 2>/dev/null
export NEWTON_LAST_FILE="$_newton_last_file"
_newton_preexec() { _newton_cmd="$1" }
_newton_precmd() {
  local st=$?
  if [[ -n "$_newton_cmd" && "$_newton_cmd" != newton && "$_newton_cmd" != newton\ * ]]; then
    print -r -- "$st"$'\n'"$_newton_cmd" >| "$_newton_last_file" 2>/dev/null
  fi
  _newton_cmd=""
}
autoload -Uz add-zsh-hook
add-zsh-hook preexec _newton_preexec
precmd_functions=(_newton_precmd ${precmd_functions:#_newton_precmd})   # first, so $? is still the command's status
fi
