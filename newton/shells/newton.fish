# ─────────────────────────────────────────────────────────────────────────────
#  Newton for fish — Think it. Tab it. Done.
#  Load with:  newton init fish | source     (in ~/.config/fish/config.fish)
#
#    Tab        plain English → command   (normal completion otherwise)
#    Tab again  cycle through alternative commands
#    Shift+Tab  put your original words back
#    Alt+N      force Newton (or press Esc then N) on the current line
# ─────────────────────────────────────────────────────────────────────────────
if status is-interactive; and not set -q __newton_loaded
    set -g __newton_loaded 1
    set -gx NEWTON_SHELL_INTEGRATION fish
    set -g __newton_alts
    set -g __newton_idx 0
    set -g __newton_last ""
    set -g __newton_orig ""
    set -g __newton_english the a an all every that which from into in on of for with my me than \
        bigger larger smaller older newer files folder folders directory directories this these those is are \
        using named called containing recursively everything each current last and or how what show list \
        to by at it its you please can i want not only any new old big large small biggest largest first top count number size sizes bytes lines line name names extension type modified created today yesterday hours days minutes ago port process processes running listening free space disk memory usage over under between per out up down again then so was be do does display get give print find where who when why inside outside text content contents whose has have had
    set -g __newton_subcmds suggest explain setup init doctor history config help plan resume plans status prompt ask chat fix commit agent update uninstall

    function __newton_is_natural --argument-names line
        set line (string trim -- $line)
        string match -q -- '#*' $line; and return 0
        test "$NEWTON_TRIGGER" = prefix; and return 1
        string match -qr -- '[|<>&;$`=\\\\"{}]' $line; and return 1
        set -l words (string split -n ' ' -- $line)
        test (count $words) -ge 3; or return 1
        for w in $words
            string match -q -- '-*' $w; and return 1
        end
        if test "$words[1]" = newton
            contains -- $words[2] $__newton_subcmds; and return 1
            return 0
        end
        type -q -- $words[1]; or return 0
        set -l hits 0
        for w in $words[2..-1]
            contains -- (string lower -- $w) $__newton_english; and set hits (math $hits + 1)
        end
        test $hits -ge 2; and return 0
        test $hits -ge 1 -a (count $words) -ge 4; or return 1
        string match -qr -- '[/.~*?@:]' $line; and return 1
        return 0
    end

    function __newton_translate
        set -l desc (commandline)
        set -l cmd; set -l note; set -l warn; set -l err; set -l alts
        printf '\r\033[2K\033[38;5;245m  ◌ newton is thinking…\033[0m' >&2
        set -l ask (string replace -r '^newton ' '' -- $desc)
        for line in (command newton suggest --porcelain --shell fish -- "$ask" 2>/dev/null)
            set -l kv (string split -m1 \t -- $line)
            switch $kv[1]
                case cmd;  set cmd $kv[2]
                case alt;  set -a alts $kv[2]
                case note; set note $kv[2]
                case warn; set warn $kv[2]
                case err;  set err $kv[2]
            end
        end
        printf '\r\033[2K' >&2
        if test -z "$cmd"
            test -n "$err"; or set err "no answer (try `newton doctor`)"
            printf '\n\033[38;5;245m  ✗ newton: %s\033[0m\n' $err >&2
            commandline -f repaint
            return
        end
        set -g __newton_orig $desc
        set -g __newton_alts $cmd $alts
        set -g __newton_idx 1
        commandline -r -- $cmd
        commandline -C (string length -- $cmd)
        set -g __newton_last $cmd
        test -n "$note"; or set note "ready — review it, then press Enter"
        set -l msg "  ❯ $note"
        test (count $alts) -gt 0; and set msg "$msg   ·  ⇥ "(count $alts)" more"
        printf '\n\033[38;5;245m%s   ·  ⇧⇥ undo\033[0m\n' $msg >&2
        test -n "$warn"; and printf '\033[38;5;214m  ▲ careful: %s\033[0m\n' $warn >&2
        commandline -f repaint
    end

    function __newton_tab
        set -l buf (commandline)
        if test -n "$__newton_last"; and test "$buf" = "$__newton_last"; and test (count $__newton_alts) -gt 1
            set -g __newton_idx (math "$__newton_idx % "(count $__newton_alts)" + 1")
            commandline -r -- $__newton_alts[$__newton_idx]
            set -g __newton_last $__newton_alts[$__newton_idx]
            commandline -f repaint
        else if __newton_is_natural "$buf"
            __newton_translate
        else
            commandline -f complete
        end
    end

    function __newton_revert
        if test -n "$__newton_last"; and test (commandline) = "$__newton_last"
            commandline -r -- $__newton_orig
            set -g __newton_last ""
        else
            commandline -f complete-and-search
        end
    end

    function __newton_force
        __newton_translate
    end

    for mode in default insert
        bind -M $mode \t __newton_tab 2>/dev/null
        bind -M $mode -k btab __newton_revert 2>/dev/null; or bind -M $mode shift-tab __newton_revert 2>/dev/null
        bind -M $mode \en __newton_force 2>/dev/null
    end

    # ── last-command memory for `newton fix` (written to a private file, never exported into child processes) ──
    set -l __nc (set -q XDG_CACHE_HOME; and echo $XDG_CACHE_HOME; or echo $HOME/.cache)/newton
    test -d $__nc; or mkdir -m 700 -p $__nc 2>/dev/null
    set -gx NEWTON_LAST_FILE $__nc/last-$fish_pid
    function __newton_postexec --on-event fish_postexec
        set -l st $status
        string match -qr '^newton( |$)' -- $argv[1]; and return
        printf '%s\n%s\n' $st "$argv[1]" > $NEWTON_LAST_FILE 2>/dev/null
    end
end
