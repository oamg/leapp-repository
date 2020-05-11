from leapp.libraries.stdlib import run


def update_kernel_config(path):
    ''' Update DEFAULTKERNEL entry at provided config file '''
    run(['/bin/sed',
         '-i',
         's/^DEFAULTKERNEL=kernel$/DEFAULTKERNEL=kernel-core/g',
         path])
