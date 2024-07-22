#!/usr/bin/python3
"""
This script validates DNS zone files in a Git repository.

It performs the following checks:
- Identifies changed files in the repository.
- Parses and validates zone files for SOA and $ORIGIN records.
- Checks the format and increment of serial numbers.
- Uses named-checkzone to validate zone files.

Usage:
    This script can be used as a Git pre-commit hook or in a CI/CD pipeline.

Modules:
    os
    sys
    subprocess
    logging
    re
    datetime

Classes:
    Call
    CommandExecutionError

Functions:
    init()
    exec_cmd(cmd)
    read_file(zonefile, revision)
    get_all_zonefiles()
    get_changed_zonefiles(repo_path)
    get_rev_count(zonefile)
    get_repo_path()
    parse_zone(data)
    check_zone(zonename, zonefile)
    parse_serial(data)
    check_serial(serial_rev0, serial_rev1)
    parse_origin(data)
    check_origin(origin_list)
    pre_commit(repo_path, file_list)
    main()

Exceptions:
    CommandExecutionError
"""


import os
import sys
import subprocess
import logging
import re
import datetime


logging.basicConfig(
#    level=logging.DEBUG, format="%(levelname)-8s %(funcName)s:%(lineno)d - %(message)s"
    level=logging.INFO, format="%(levelname)-8s %(message)s"
)


class Call:
    """
    Singleton class to maintain method information.
    """
    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super(Call, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            self.method = None
            self.initialized = True


class CommandExecutionError(Exception):
    """
    Custom exception class for command execution errors.

    Attributes:
        returncode (int): The return code of the failed command.
        output (str): The output (stdout or stderr) of the failed command.
    """
    def __init__(self, returncode, output):
        self.returncode = returncode
        self.output = output
        super().__init__(self.output)


def init():
    """
    Initialize the call method based on the execution context.
    """
    call = Call()
    if ".git/hooks" in os.path.abspath(sys.argv[0]):
        logging.debug("Call method: git hook")
        call.method = "git-hook"
    else:
        logging.debug("Call method: ci/cd pipeline")
        call.method = "ci-cd"


def exec_cmd(cmd):
    """
    Execute a command and capture its output.

    Args:
        cmd (list): The command to execute.

    Returns:
        subprocess.CompletedProcess: The result of the executed command.

    Raises:
        CommandExecutionError: If the command fails.
    """
    try:
        logging.debug("Executing command: %s", subprocess.list2cmdline(cmd))
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True
        )
        return result
    except subprocess.CalledProcessError as cpe_error:
        logging.debug(
            "Command execution '%s' finished with errors", subprocess.list2cmdline(cmd)
        )
        raise CommandExecutionError(
            cpe_error.returncode,
            cpe_error.stderr.strip() or cpe_error.stdout.strip()
        )


def read_file(zonefile, revision):
    """
    Read the content of a file at a specific revision.

    Args:
        zonefile (str: Path to the zone file.
        revision (int): The revision to read (0 for current, 1 for previous).

    Returns:
        str: The content of the file.
    """
    call = Call()
    cmd = ["git", "show"]
    if call.method == "git-hook" and revision == 0:
        cmd += [":" + zonefile]
    if call.method == "git-hook" and revision == 1:
        cmd += ["HEAD:" + zonefile]
    if call.method == "ci-cd" and revision == 0:
        cmd += ["HEAD:" + zonefile]
    if call.method == "ci-cd" and revision == 1:
        cmd += ["HEAD~1:" + zonefile]

    result = exec_cmd(cmd)
    data = result.stdout.splitlines()
    data = "\n".join(data)
    return data


def get_all_zonefiles():
    """
    Get a list of all zonefiles in the repository.

    Args:
        repo_path (str): Path to the git repository.

    Returns:
        list: List of all files.
    """
    cmd = ["git", "ls-files"]

    result = exec_cmd(cmd)
    file_list = result.stdout.split("\n")
    file_list = list(filter(None, file_list))

    pattern = re.compile(r"^db\.|\.db$|\.zone$|\.rev$|\.rpz$")
    for item in file_list:
        if not pattern.search(os.path.basename(item)):
            file_list.remove(item)

    logging.info("%d file(s) detected", len(file_list))
    return file_list


def get_changed_zonefiles(repo_path):
    """
    Get a list of changed zonefiles in the repository.

    Args:
        repo_path (str): Path to the git repository.

    Returns:
        list: List of changed files.
    """
    call = Call()
    cmd = [
        "git",
        "--git-dir=" + repo_path + "/.git",
        "--work-tree=" + repo_path,
        "diff",
        "--name-only",
        "--diff-filter=d",
    ]
    if call.method == "git-hook":
        cmd += ["HEAD"]
    if call.method == "ci-cd":
        cmd += ["HEAD~1", "HEAD"]

    result = exec_cmd(cmd)
    file_list = result.stdout.split("\n")
    file_list = list(filter(None, file_list))

    pattern = re.compile(r"^db\.|\.db$|\.zone$|\.rev$|\.rpz$")
    for item in file_list:
        if not pattern.search(os.path.basename(item)):
            file_list.remove(item)

    logging.info("%d changed file(s) detected", len(file_list))
    return file_list


def get_rev_count(zonefile):
    """
    Get the revision count for a specific file in the repository.

    Args:
        zonefile (str or None): Path to the zone file.

    Returns:
        int: The revision count.
    """
    call = Call()
    cmd = ["git", "rev-list", "--count", "HEAD"]
    if zonefile:
        cmd += ["--", zonefile]

    try:
        result = exec_cmd(cmd)
    except:
        rev_count = 0
    else:
        if call.method == "git-hook":
            rev_count = int(result.stdout)
        if call.method == "ci-cd":
            rev_count = int(result.stdout) - 1

    logging.debug("Revision: %d", rev_count)
    return rev_count


def get_repo_path():
    """
    Get the top-level path of the current Git repository.

    Returns:
        str: The top-level path of the Git repository.

    Raises:
        SystemExit: If not inside a Git repository.
    """
    cmd = ["git", "-C", os.getcwd(), "rev-parse", "--show-toplevel"]

    try:
        result = exec_cmd(cmd)
        repo_path = result.stdout.split("\n")
        logging.info("Repo path is: %s", repo_path[0])
        return repo_path[0]
    except CommandExecutionError:
        logging.error("You are not inside a git repo")
        sys.exit(1)


def parse_zone(data):
    """
    Parse the zone name from the zone file content.

    Args:
        data (str): The content of the zone file.

    Returns:
        str: The parsed zone name.

    Raises:
        SystemExit: If the zone name cannot be parsed.
    """
    soa_pattern = r"^\s*([a-zA-Z0-9-]+[a-zA-Z0-9-\.]+)\s+IN\s+SOA"
    origin_pattern = r"^\s*\$ORIGIN\s+([a-zA-Z0-9-]+[a-zA-Z0-9-\.]+)"

    match_soa = re.search(soa_pattern, data, re.MULTILINE)
    if match_soa:
        zonename = match_soa.group(1).strip(".")
        logging.debug("Parsed zonename from SOA record: %s", zonename)
        return zonename

    match_origin = re.search(origin_pattern, data, re.MULTILINE)
    if match_origin:
        zonename = match_origin.group(1).strip(".")
        logging.debug("Parsed zonename from $ORIGIN directive: %s", zonename)
        return zonename

    logging.critical("Failed to parse zonename")
    sys.exit(1)


def check_zone(zonename, zonefile):
    """
    Check the validity of a zone file using named-checkzone.

    Args:
        zonename (str): The name of the zone.
        zonefile (str): Path to the zone file.

    Returns:
        int: The return code of named-checkzone.
    """
    cmd = ["named-checkzone", "-k", "fail", zonename, zonefile]

    try:
        result = exec_cmd(cmd)
        logging.info("Zone OK")
        return result.returncode
    except CommandExecutionError as error:
        logging.error("Errors in validating zone %s:\n%s", zonename, error.output)
        return error.returncode


def parse_serial(data):
    """
    Parse the serial number from the zone file content.

    Args:
        data (str): The content of the zone file.

    Returns:
        int: The parsed serial number.

    Raises:
        SystemExit: If the serial number cannot be parsed.
    """
    pattern = r"IN\s+SOA\s+[A-Za-z0-9-\.]+\s+[A-Za-z0-9-\.]+\s+\(\s+(\d+)"

    match = re.search(pattern, data)
    if match:
        serial = int(match.group(1))
        logging.debug("Parsed serial: %d", serial)
        return serial

    logging.critical("Failed to parse serial")
    sys.exit(1)


def check_serial(serial_rev0, serial_rev1):
    """
    Check the format and value of the serial number.

    Args:
        serial_rev0 (int): The current serial number.
        serial_rev1 (int or None): The previous serial number (None if not available).

    Returns:
        int: Error count (0 if no errors, 1 if errors found).
    """
    err_counter = 0
    sys_time = datetime.datetime.now()
    date = sys_time.strftime("%Y%m%d")
    logging.debug("Current system time is %s", sys_time)

    logging.debug("Checking serial format: %d", serial_rev0)
    if serial_rev1 is None:
        pattern = r"19[7-9][0-9]|[2-9][0-9]{3}0[1-9]|1[12][012][0-9]|3[01]\d\d"
    else:
        pattern = rf"^{date}\d\d$"
    match = re.search(pattern, str(serial_rev0))
    if match:
        logging.info("Serial format OK")
    else:
        logging.error("Bad serial number format")
        err_counter = 1

    if serial_rev1 is not None:
        logging.debug("Checking serial %d against serial %d", serial_rev0, serial_rev1)
        if serial_rev0 > serial_rev1:
            logging.info("Serial number incrementation OK")
        else:
            logging.error("Serial number was not incremented")
            err_counter = 1

    return err_counter


def parse_origin(data):
    """
    Parse the $ORIGIN directives from the zone file content.

    Args:
        data (str): The content of the zone file.

    Returns:
        list: List of $ORIGIN directives.
    """
    pattern = r"^[ \t]*\$ORIGIN.*$"
    match = re.findall(pattern, data, re.MULTILINE)
    logging.debug("$ORIGIN directive(s): %s", match)
    return match


def check_origin(origin_list):
    """
    Check the format of the $ORIGIN directives.

    Args:
        origin_list (list): List of $ORIGIN directives.

    Returns:
        int: Error count (0 if no errors, 1 if errors found).
    """
    err_counter = 0

    for line in origin_list:
        pattern = r"^[ \t]*\$ORIGIN.*\.$"
        match = re.search(pattern, line)
        if match:
            logging.info("%s OK", line)
        else:
            logging.error('No trailing "." at %s', line)
            err_counter = 1
    return err_counter


def pre_commit(repo_path, file_list):
    """
    Perform pre-commit checks on the zone files.

    Args:
        repo_path (str): Path to the Git repository.
        file_list (list): List of files.

    Raises:
        SystemExit: If any errors are found.
    """
    err_counter = 0

    for zonefile in file_list:
        logging.info("Checking zonefile %s ...", zonefile)

        tmp_counter = err_counter
        rev_counter = get_rev_count(zonefile)

        zonename = parse_zone(read_file(zonefile, 0))
        err_counter += check_zone(zonename, os.path.join(repo_path, zonefile))

        if tmp_counter == err_counter and rev_counter == 0:
            serial_rev0 = parse_serial(read_file(zonefile, 0))
            err_counter += check_serial(serial_rev0, None)

        if tmp_counter == err_counter and rev_counter > 0:
            serial_rev0 = parse_serial(read_file(zonefile, 0))
            serial_rev1 = parse_serial(read_file(zonefile, 1))
            err_counter += check_serial(serial_rev0, serial_rev1)

        if tmp_counter == err_counter:
            origin_list = parse_origin(read_file(zonefile, 0))
            err_counter += check_origin(origin_list)

    if err_counter:
        sys.exit(1)


def main():
    """
    Main function to determine the execution method and perform pre-commit checks.
    """
    init()

    repo_path = get_repo_path()
    rev_count = get_rev_count(None)

    if rev_count == 0:
        file_list = get_all_zonefiles()
    if rev_count > 0:
        file_list = get_changed_zonefiles(repo_path)

    pre_commit(repo_path, file_list)


if __name__ == "__main__":
    main()
