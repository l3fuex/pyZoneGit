# DNS Zone File Validator (pyZoneGit)

This script validates DNS zone files in a Git repository. It does so by identifying files that have been modified in the repository and running certain checks on them. These checks consist of verifying the integrity of the zone file using the `named-checkzone` utility from the `bind9utils` package, checking if the $ORIGIN directive ends with a dot, checking if the serial number format corresponds to YYYYMMDDXX, and, in case there is an older revision of the file, verifying if the serial number has been incremented.

To execute the `named-checkzone` command, the logic needs to parse the zone name from a given zone file. At this point, the program only supports zone files where the zone name can either be parsed from the $ORIGIN directive or from the SOA Record. Zone files with no zone name in them, like the db.example.net zone file in the testing directory, are not supported as of now.

## Dependencies
- Python 3.x
- bind9utils package

## Installation

```bash
# Install dependencies
sudo apt install python3 bind9utils

# Copy the code to your machine
git clone https://github.com/l3fuex/pyZoneGit

# Make the script executable
chmod +x pyZonGit/pyZoneGit.py

# Put a link named pre-commit in the .git/hook directory of the repo which holds the zone files
ln -s /path/to/pyZoneGit.py /path/to/zonefile-repo/.git/hooks/pre-commit
````

## Usage
The program can either be used as a pre-commit hook on the client side or in a CI/CD pipeline. The difference in the logic lies in how changed files are detected. When used as a pre-commit hook, the changed files have to be determined before the commit is finalized. Conversely, when used in a CI/CD pipeline, the commit has already taken place, so the changed files have to be determined in a post-commit manner.

### Git hook
Git hooks are scripts that Git executes on specific events in the Git lifecycle. Hooks reside in the .git/hooks directory of a Git repository and are triggered by various Git commands. To use the script as a pre-commit hook to automatically validate the changes before a commit is finalized, simply place a link to the script in the .git/hooks directory of the repository containing the zone files and name it pre-commit like it is outlined in the installation section.

```bash
# A commit triggers the pre-commit hook
git commit -m "trigger the pre-commit hook"
```
```bash
# Possible ouput
INFO     Repo path is: /path/to/zonefile-repo
INFO     1 changed file(s) detected
INFO     Checking zonefile db.example.at ...
INFO     Zone OK
INFO     Serial format OK
ERROR    Serial number was not incremented
```

### CI/CD Pipeline
Due to the fact that the validation of the changes and the usage of the script as a pre-commit hook rely completely on the responsible administrators, an additional check should be carried out somewhere in the workflow where it can't be overridden. A CI/CD pipeline, which automates software testing and deployment tasks, would be one way to achieve that. Therefore, the program is also designed to work when triggered as a script in such a pipeline. See the `.gitlab-ci.yml.sample` file for an example of how such a pipeline could look like in gitlab.

## License
This software is provided under the [Creative Commons BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) license.
