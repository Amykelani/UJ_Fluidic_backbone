/*
 Name:		Fluidic_backbone_arduino.ino
 Created:	2/1/2021 2:12:29 PM
 Author:	mattn
*/

//include core libraries
#include <CommandHandler.h>
#include <CommandManager.h>

CommandManager cmdMng;

//include module driver libraries
#include <AccelStepper.h>
#include <LinearAccelStepperActuator.h>
#include <CommandAnalogRead.h>
#include <CommandAnalogWrite.h>
#include <CommandAccelStepper.h>
#include <CommandLinearAccelStepperActuator.h>
#include <CommandDigitalWrite.h>
<<<<<<< HEAD
//#include <CommandDigitalRead.h>

//initialised module objects
AccelStepper stpx(AccelStepper::DRIVER, 54, 55);
CommandLinearAccelStepperActuator cmdStpx(stpx, 3, 38);

AccelStepper stpy(AccelStepper::DRIVER, 60, 61);
CommandLinearAccelStepperActuator cmdStpy(stpy, 2, 56);

AccelStepper stpz(AccelStepper::DRIVER, 46, 48);
CommandAccelStepper cmdStpz(stpz, 62);

AccelStepper stpe0(AccelStepper::DRIVER, 26, 28);
CommandAccelStepper cmdStpe0(stpe0, 24);

AccelStepper stpe1(AccelStepper::DRIVER, 36, 34);
CommandAccelStepper cmdStpe1(stpe1, 30);
=======
#include <CommandDigitalRead.h>

//initialised module objects
AccelStepper stpx(AccelStepper::DRIVER, 54, 55);
CommandLinearAccelStepperActuator cmdStpx(stpx, 3);

AccelStepper stpy(AccelStepper::DRIVER, 60, 61);
CommandLinearAccelStepperActuator cmdStpy(stpy, 2);

AccelStepper stpz(AccelStepper::DRIVER, 46, 48);
CommandAccelStepper cmdStpz(stpz);

AccelStepper stpe0(AccelStepper::DRIVER, 26, 28);
CommandAccelStepper cmdStpe0(stpe0);
>>>>>>> 8b5369b3a1713a25e9057e6ee629d00983291042

//enable pins
CommandDigitalWrite enx(38);
CommandDigitalWrite eny(56);
CommandDigitalWrite enz(62);
CommandDigitalWrite ene0(24);
<<<<<<< HEAD
CommandDigitalWrite ene1(30);
=======
>>>>>>> 8b5369b3a1713a25e9057e6ee629d00983291042

CommandAnalogRead ar1(A3);
CommandAnalogRead ar2(A4);

CommandAnalogRead t1(A13);
<<<<<<< HEAD

//PWM pins
CommandAnalogWrite aw1(8);
CommandAnalogWrite aw2(9);
=======
CommandAnalogRead t2(A14);

//PWM pins
CommandAnalogWrite aw1(9);
CommandAnalogWrite aw2(10);

//Digital read pins
CommandDigitalRead dr1(63);
CommandDigitalRead dr2(59);

//Digital write pins
CommandDigitalWrite dw1(16);
CommandDigitalWrite dw2(17);

>>>>>>> 8b5369b3a1713a25e9057e6ee629d00983291042

void setup() {
	//register modules with commandmanager
	Serial.begin(115200);
	cmdStpx.registerToCommandManager(cmdMng, "STPX");
	cmdStpy.registerToCommandManager(cmdMng, "STPY");
	cmdStpz.registerToCommandManager(cmdMng, "STPZ");
	cmdStpe0.registerToCommandManager(cmdMng, "STPE0");
<<<<<<< HEAD
  cmdStpe1.registerToCommandManager(cmdMng, "STPE1");
=======
>>>>>>> 8b5369b3a1713a25e9057e6ee629d00983291042

	enx.registerToCommandManager(cmdMng, "ENX");
	eny.registerToCommandManager(cmdMng, "ENY");
	enz.registerToCommandManager(cmdMng, "ENZ");
	ene0.registerToCommandManager(cmdMng, "ENE0");
<<<<<<< HEAD
  ene1.registerToCommandManager(cmdMng, "ENE1");
=======
>>>>>>> 8b5369b3a1713a25e9057e6ee629d00983291042

	ar1.registerToCommandManager(cmdMng, "AR1");
	ar2.registerToCommandManager(cmdMng, "AR2");

	t1.registerToCommandManager(cmdMng, "T1");
<<<<<<< HEAD

	aw1.registerToCommandManager(cmdMng, "AW1");
	aw2.registerToCommandManager(cmdMng, "AW2");
=======
	t2.registerToCommandManager(cmdMng, "T2");

	aw1.registerToCommandManager(cmdMng, "STIR");
	aw2.registerToCommandManager(cmdMng, "HCAP");

	dr1.registerToCommandManager(cmdMng, "DR1");
	dr2.registerToCommandManager(cmdMng, "DR2");

	dw1.registerToCommandManager(cmdMng, "DW1");
	dw2.registerToCommandManager(cmdMng, "DW2");
>>>>>>> 8b5369b3a1713a25e9057e6ee629d00983291042

	cmdMng.init();
}

void loop() {
	cmdMng.update();
}
