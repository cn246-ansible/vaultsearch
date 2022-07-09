# vaultsearch

`vaultsearch` is a Python 3 script that uses built-in Python and Ansible modules
to recursively search for given terms in all found vault files.

If you configured `vault_password_file` in **ansible.cfg**, it will use that -- 
otherwise, it will prompt for the vault password upon usage.

**Note:** I don't think it will find vault encrypted strings as I rarely use them
and didn't consider them while writing the script.

----

## Install
- Clone the repo or download the file.
- Copy or symlink the script to somewhere in your `$PATH`.
- It is also possible to place the script in the top level of the playbook and run it from there.

## Usage
- Recursively search all vault files starting in your current working directory:
```
vaultsearch 'searchterm'
```
- For a shorter file path output use `.` as a location:
```
vaultsearch 'searchterm' .
```
- Recursively search all vault files starting from specified directory:
```
vaultsearch 'searchterm' host_vars/myhost
```
- Recursively search with regex patterns (I haven't tested many regex patterns yet):
```
vaultsearch 'searchterm|otherterm' group_vars/all
```

----

### Additional Information
I had originally used a bash script which worked well, but took a long time when
parsing the entire playbook.

Initial testing on a medium sized playbook shows this script can be up to 20x faster!:
```
# Bash Script
time vaultgrep 'user_001' .
<--snip-->
real    1m31.351s
user    1m21.560s
sys     0m8.327s

# Python Script
time vaultsearch 'user_001' .
<--snip-->
real    0m3.795s
user    0m3.743s
sys     0m0.044s
```

### Disclaimer
I do not have much experience with Python and pieced this together with snippets
that I found from around the web.

Any pull requests improving the code and/or performance are welcomed.

