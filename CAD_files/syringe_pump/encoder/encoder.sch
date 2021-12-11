EESchema Schematic File Version 4
EELAYER 30 0
EELAYER END
$Descr A4 11693 8268
encoding utf-8
Sheet 1 1
Title ""
Date ""
Rev ""
Comp ""
Comment1 ""
Comment2 ""
Comment3 ""
Comment4 ""
$EndDescr
$Comp
L power:GND #PWR?
U 1 1 61A430F4
P 2750 4400
F 0 "#PWR?" H 2750 4150 50  0001 C CNN
F 1 "GND" H 2755 4227 50  0000 C CNN
F 2 "" H 2750 4400 50  0001 C CNN
F 3 "" H 2750 4400 50  0001 C CNN
	1    2750 4400
	1    0    0    -1  
$EndComp
$Comp
L power:+5V #PWR?
U 1 1 61A482B9
P 2750 3800
F 0 "#PWR?" H 2750 3650 50  0001 C CNN
F 1 "+5V" H 2765 3973 50  0000 C CNN
F 2 "" H 2750 3800 50  0001 C CNN
F 3 "" H 2750 3800 50  0001 C CNN
	1    2750 3800
	1    0    0    -1  
$EndComp
$Comp
L Comparator:LM393 U1
U 3 1 61A3F7D7
P 2850 4100
F 0 "U1" H 2808 4146 50  0000 L CNN
F 1 "LM393" H 2808 4055 50  0000 L CNN
F 2 "" H 2850 4100 50  0001 C CNN
F 3 "http://www.ti.com/lit/ds/symlink/lm393.pdf" H 2850 4100 50  0001 C CNN
	3    2850 4100
	1    0    0    -1  
$EndComp
$Comp
L Device:R R6
U 1 1 61A3A1C2
P 3100 3400
F 0 "R6" H 3030 3354 50  0000 R CNN
F 1 "220E" H 3030 3445 50  0000 R CNN
F 2 "" V 3030 3400 50  0001 C CNN
F 3 "~" H 3100 3400 50  0001 C CNN
	1    3100 3400
	-1   0    0    1   
$EndComp
Wire Wire Line
	3100 3250 3100 3000
$Comp
L power:+5V #PWR?
U 1 1 61A3AB48
P 3250 2700
F 0 "#PWR?" H 3250 2550 50  0001 C CNN
F 1 "+5V" H 3265 2873 50  0000 C CNN
F 2 "" H 3250 2700 50  0001 C CNN
F 3 "" H 3250 2700 50  0001 C CNN
	1    3250 2700
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR?
U 1 1 61A3BEE8
P 3100 3550
F 0 "#PWR?" H 3100 3300 50  0001 C CNN
F 1 "GND" H 3105 3377 50  0000 C CNN
F 2 "" H 3100 3550 50  0001 C CNN
F 3 "" H 3100 3550 50  0001 C CNN
	1    3100 3550
	1    0    0    -1  
$EndComp
$Comp
L power:+5V #PWR?
U 1 1 61A41317
P 4050 2700
F 0 "#PWR?" H 4050 2550 50  0001 C CNN
F 1 "+5V" H 4065 2873 50  0000 C CNN
F 2 "" H 4050 2700 50  0001 C CNN
F 3 "" H 4050 2700 50  0001 C CNN
	1    4050 2700
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR?
U 1 1 61A46485
P 3250 4850
F 0 "#PWR?" H 3250 4600 50  0001 C CNN
F 1 "GND" H 3255 4677 50  0000 C CNN
F 2 "" H 3250 4850 50  0001 C CNN
F 3 "" H 3250 4850 50  0001 C CNN
	1    3250 4850
	1    0    0    -1  
$EndComp
Wire Wire Line
	3250 4450 3250 4800
Wire Wire Line
	3250 4800 4100 4800
Connection ~ 3250 4800
Wire Wire Line
	3250 4800 3250 4850
$Comp
L Connector:Conn_01x03_Male J1
U 1 1 61A48F52
P 6600 3650
F 0 "J1" H 6550 3750 50  0000 R CNN
F 1 "Conn_01x03_Male" H 6750 3850 50  0000 R CNN
F 2 "" H 6600 3650 50  0001 C CNN
F 3 "~" H 6600 3650 50  0001 C CNN
	1    6600 3650
	-1   0    0    1   
$EndComp
$Comp
L power:+5V #PWR?
U 1 1 61A49EF3
P 6150 3550
F 0 "#PWR?" H 6150 3400 50  0001 C CNN
F 1 "+5V" H 6165 3723 50  0000 C CNN
F 2 "" H 6150 3550 50  0001 C CNN
F 3 "" H 6150 3550 50  0001 C CNN
	1    6150 3550
	1    0    0    -1  
$EndComp
Wire Wire Line
	6150 3550 6400 3550
Wire Wire Line
	6400 3950 6400 3750
Wire Wire Line
	4050 3000 4200 3000
Wire Wire Line
	4050 2900 4050 2700
Wire Wire Line
	3100 3000 3250 3000
Wire Wire Line
	3250 2700 3250 2900
Wire Wire Line
	3750 3850 4050 3850
Wire Wire Line
	5600 3950 6400 3950
Connection ~ 5600 3750
Wire Wire Line
	5600 3750 5600 3950
Wire Wire Line
	5850 3650 6400 3650
$Comp
L power:GND #PWR?
U 1 1 61A4AE1A
P 5850 3650
F 0 "#PWR?" H 5850 3400 50  0001 C CNN
F 1 "GND" H 5855 3477 50  0000 C CNN
F 2 "" H 5850 3650 50  0001 C CNN
F 3 "" H 5850 3650 50  0001 C CNN
	1    5850 3650
	1    0    0    -1  
$EndComp
Connection ~ 3500 4450
$Comp
L Comparator:LM393 U1
U 2 1 61A47CE1
P 3800 4350
F 0 "U1" H 3800 4650 50  0000 C CNN
F 1 "LM393" H 3800 4550 50  0000 C CNN
F 2 "" H 3800 4350 50  0001 C CNN
F 3 "http://www.ti.com/lit/ds/symlink/lm393.pdf" H 3800 4350 50  0001 C CNN
	2    3800 4350
	1    0    0    -1  
$EndComp
Wire Wire Line
	4100 4800 4100 4350
Wire Wire Line
	3500 4450 3250 4450
Wire Wire Line
	3500 4250 3500 4450
Wire Wire Line
	4200 3000 4200 3150
$Comp
L TCST2103:TCST2103 K1
U 1 1 61A37AB7
P 3250 2900
F 0 "K1" H 3650 3165 50  0000 C CNN
F 1 "TCST2103" H 3650 3074 50  0000 C CNN
F 2 "DIPS254W40P760L2450H1110Q4N" H 3900 3000 50  0001 L CNN
F 3 "https://componentsearchengine.com/Datasheets/2/TCST2103.pdf" H 3900 2900 50  0001 L CNN
F 4 "Photointerrupter Transmissive 3.1mm" H 3900 2800 50  0001 L CNN "Description"
F 5 "11.1" H 3900 2700 50  0001 L CNN "Height"
F 6 "Vishay" H 3900 2600 50  0001 L CNN "Manufacturer_Name"
F 7 "TCST2103" H 3900 2500 50  0001 L CNN "Manufacturer_Part_Number"
F 8 "782-TCST2103" H 3900 2400 50  0001 L CNN "Mouser Part Number"
F 9 "https://www.mouser.co.uk/ProductDetail/Vishay-Semiconductors/TCST2103?qs=%2Fjqivxn91cc%252BOKE9BUKCsA%3D%3D" H 3900 2300 50  0001 L CNN "Mouser Price/Stock"
F 10 "TCST2103" H 3900 2200 50  0001 L CNN "Arrow Part Number"
F 11 "https://www.arrow.com/en/products/tcst2103/vishay" H 3900 2100 50  0001 L CNN "Arrow Price/Stock"
	1    3250 2900
	1    0    0    -1  
$EndComp
$Comp
L power:+5V #PWR?
U 1 1 61A48E8A
P 5600 3300
F 0 "#PWR?" H 5600 3150 50  0001 C CNN
F 1 "+5V" H 5615 3473 50  0000 C CNN
F 2 "" H 5600 3300 50  0001 C CNN
F 3 "" H 5600 3300 50  0001 C CNN
	1    5600 3300
	1    0    0    -1  
$EndComp
$Comp
L power:GND #PWR?
U 1 1 61A46A37
P 4500 4350
F 0 "#PWR?" H 4500 4100 50  0001 C CNN
F 1 "GND" H 4505 4177 50  0000 C CNN
F 2 "" H 4500 4350 50  0001 C CNN
F 3 "" H 4500 4350 50  0001 C CNN
	1    4500 4350
	1    0    0    -1  
$EndComp
Wire Wire Line
	4500 3650 4650 3650
Connection ~ 4500 3650
Wire Wire Line
	4500 3200 4500 3650
Wire Wire Line
	4800 3200 4500 3200
Wire Wire Line
	5350 3750 5250 3750
Connection ~ 5350 3750
Wire Wire Line
	5350 3200 5350 3750
Wire Wire Line
	5100 3200 5350 3200
Wire Wire Line
	5600 3750 5350 3750
Wire Wire Line
	5600 3600 5600 3750
Wire Wire Line
	4200 3650 4500 3650
Wire Wire Line
	4200 3450 4200 3650
Wire Wire Line
	4500 3850 4650 3850
Connection ~ 4500 3850
Wire Wire Line
	4500 3850 4500 4050
Wire Wire Line
	4350 3850 4500 3850
$Comp
L power:+5V #PWR?
U 1 1 61A42A86
P 3750 3850
F 0 "#PWR?" H 3750 3700 50  0001 C CNN
F 1 "+5V" V 3765 3978 50  0000 L CNN
F 2 "" H 3750 3850 50  0001 C CNN
F 3 "" H 3750 3850 50  0001 C CNN
	1    3750 3850
	1    0    0    -1  
$EndComp
$Comp
L Device:R R5
U 1 1 61A427C7
P 4500 4200
F 0 "R5" H 4570 4246 50  0000 L CNN
F 1 "3.3k" H 4570 4155 50  0000 L CNN
F 2 "" V 4430 4200 50  0001 C CNN
F 3 "~" H 4500 4200 50  0001 C CNN
	1    4500 4200
	1    0    0    -1  
$EndComp
$Comp
L Device:R R1
U 1 1 61A42513
P 4200 3300
F 0 "R1" H 4130 3254 50  0000 R CNN
F 1 "1.1k" H 4130 3345 50  0000 R CNN
F 2 "" V 4130 3300 50  0001 C CNN
F 3 "~" H 4200 3300 50  0001 C CNN
	1    4200 3300
	-1   0    0    1   
$EndComp
$Comp
L Device:R R3
U 1 1 61A41BE8
P 5600 3450
F 0 "R3" H 5530 3404 50  0000 R CNN
F 1 "3.3k" H 5530 3495 50  0000 R CNN
F 2 "" V 5530 3450 50  0001 C CNN
F 3 "~" H 5600 3450 50  0001 C CNN
	1    5600 3450
	-1   0    0    1   
$EndComp
$Comp
L Device:R R2
U 1 1 61A41133
P 4950 3200
F 0 "R2" V 4743 3200 50  0000 C CNN
F 1 "3.3k" V 4834 3200 50  0000 C CNN
F 2 "" V 4880 3200 50  0001 C CNN
F 3 "~" H 4950 3200 50  0001 C CNN
	1    4950 3200
	0    1    1    0   
$EndComp
$Comp
L Device:R R4
U 1 1 61A404E4
P 4200 3850
F 0 "R4" V 4400 3850 50  0000 C CNN
F 1 "2.2k" V 4300 3850 50  0000 C CNN
F 2 "" V 4130 3850 50  0001 C CNN
F 3 "~" H 4200 3850 50  0001 C CNN
	1    4200 3850
	0    1    1    0   
$EndComp
$Comp
L Comparator:LM393 U1
U 1 1 61A3ED04
P 4950 3750
F 0 "U1" H 4950 4117 50  0000 C CNN
F 1 "LM393" H 4950 4000 50  0000 C CNN
F 2 "" H 4950 3750 50  0001 C CNN
F 3 "http://www.ti.com/lit/ds/symlink/lm393.pdf" H 4950 3750 50  0001 C CNN
	1    4950 3750
	1    0    0    -1  
$EndComp
$EndSCHEMATC