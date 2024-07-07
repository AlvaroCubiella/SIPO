from DBS import DBS

bat = DBS('COM12')
bat.Read()
print(bat.Get_Z_Metros())
