

def append_string(path, content):
    with open(path, 'a') as f:
        f.write(content)


# rpm : the default config file
vim_configs = {
    'vim-minimal': '/etc/virc',
    'vim-enhanced': '/etc/vimrc'
}


# list of macros that should be set
new_macros = [
    'let skip_defaults_vim=1',
    'set t_BE='
]


def update_config(path, append_function=append_string):
    """
    Insert expected content into the file on the path

    :param str path: string representing the full path of the config file
    """
    fmt_input = "\n{comment_line}\n{content}\n".format(comment_line='" content added by Leapp',
                                                       content='\n'.join(new_macros))

    try:
        append_function(path, fmt_input)
    except IOError:
        raise IOError('Error during writing to file: {}.'.format(path))
