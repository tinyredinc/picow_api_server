import storage
import board
import digitalio

io_switch = digitalio.DigitalInOut(board.GP22)
io_switch.direction = digitalio.Direction.INPUT
io_switch.pull = digitalio.Pull.UP

storage.remount("/", readonly=io_switch.value)