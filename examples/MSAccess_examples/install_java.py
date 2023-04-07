"""
OpenJDK Java Temporary/Local installation to support MS Access examples.

The current implementation of the MSAccess SQLDriver uses the JPype library to interface
with the UCanAccess java JDBC driver, which requires Java to be installed in order to
run.  This also serves as an example to automatically download a local Java installation
for your own projects.
"""
import jdk
import os
import pysimplesql as ss
import PySimpleGUI as sg
import subprocess


# -------------------------------------------------
# ROUTINES TO INSTALL JAVA IF USER DOES NOT HAVE IT
# -------------------------------------------------
def _is_java_installed():
    # Returns True if Java is installed, False otherwise
    try:
        subprocess.check_output(["which", "java"])
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def java_check_install(version: str = "11", jre: bool = True) -> bool:
    """
    Checks to see if Java is installed. If it is not installed, then a local
    installation process can start automatically with user permission.

    :param version: The OpenJDK version to install
    :param jre: True to install the JRE runtime, False to install the full JDK
    :returns: True if it is ok to proceed after this call, False otherwise
    """
    if not _is_java_installed():
        res = sg.popup_yes_no(
            "Java is required but not installed.  Would you like to install it?",
            title="Java not found",
        )
        if res == "Yes":
            pa = ss.ProgressAnimation("Installing Java Open-JDK JRE")
            # Update the default phrases shown in the ProgressAnimation
            config = {
                "phrases": [
                    "Please wait while OpenJDK JRE is installed locally...",
                    "Still working... Thank you for your patience.",
                ]
            }
            pa.animate(config=config)
            try:
                java_home = jdk.install(version, jre=jre)
            except Exception as e:  # noqa: BLE001
                print(e)
                sg.popup(f"There was an error installing Java: {e}")
                pa.close()
                return False
            pa.close()
            # set JAVA_HOME
            os.environ["JAVA_HOME"] = java_home
        else:
            url = jdk.get_download_url(version, jre=jre)
            sg.popup(
                f"Java is required to run this example.  You can download it at: {url}"
            )
            return False

    if not os.environ.get("JAVA_HOME"):
        sg.popup("'JAVA_HOME' must be set in order to run this example")
        return False

    return True


if __name__ == "__main__":
    if java_check_install():
        print("Java is installed.")
    else:
        print("Java is not installed.")
    exit(0)
