# Update niri_tweaks from upstream
update-scripts:
    git subtree pull --prefix=scripts https://github.com/heyoeyo/niri_tweaks.git main --squash

# Ignore local changes to output.kdl (machine-specific config)
skip-output:
    git update-index --skip-worktree conf.d/output.kdl

# Restore tracking of output.kdl
track-output:
    git update-index --no-skip-worktree conf.d/output.kdl
