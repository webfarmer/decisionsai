import AppKit

# Add this line before creating the QApplication
AppKit.NSBundle.mainBundle().infoDictionary()['LSUIElement'] = '1'

from distr.actions import transcribe
from distr.app import run

# Main execution block
if __name__ == "__main__":
    print("Starting Decisions...")
    print("Please note: that this is an early version and may not work as expected.")
    print("It may take a while to start up initially, as it needs to download model weights.")
    run()



