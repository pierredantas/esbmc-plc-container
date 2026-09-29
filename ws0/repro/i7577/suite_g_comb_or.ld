<?xml version="1.0" encoding="utf-8"?>
<project xmlns="http://www.plcopen.org/xml/tc6_0200">
  <fileHeader companyName="Anonymous" productName="Benchmark Suite" productVersion="1.0" creationDateTime="2026-08-26T00:00:00" />
  <contentHeader name="g_comb_or"><coordinateInfo><fbd><scaling x="1" y="1" /></fbd><ld><scaling x="1" y="1" /></ld><sfc><scaling x="1" y="1" /></sfc></coordinateInfo></contentHeader>
  <types><dataTypes /><pous><pou name="g_comb_or" pouType="program">
    <interface><inputVars><variable name="A"><type><BOOL /></type></variable><variable name="B"><type><BOOL /></type></variable></inputVars><outputVars><variable name="Y"><type><BOOL /></type></variable></outputVars></interface>
    <body><LD>
      <leftPowerRail localId="0"><position x="0" y="0" /><connectionPointOut formalParameter="none" /></leftPowerRail>
      <contact localId="3" negated="false" storage="none" edge="none"><position x="20" y="10" /><connectionPointIn><connection refLocalId="0" /></connectionPointIn><connectionPointOut /><variable>A</variable></contact><contact localId="4" negated="false" storage="none" edge="none"><position x="20" y="40" /><connectionPointIn><connection refLocalId="0" /></connectionPointIn><connectionPointOut /><variable>B</variable></contact><coil localId="5" negated="false" storage="none"><position x="80" y="10" /><connectionPointIn><connection refLocalId="3" /><connection refLocalId="4" /></connectionPointIn><connectionPointOut /><variable>Y</variable></coil>
      <rightPowerRail localId="2147483646"><position x="400" y="0" /><connectionPointIn /></rightPowerRail>
    </LD></body>
  </pou></pous></types>
  <instances><configurations><configuration name="Config0"><resource name="Res0"><task name="tcyclic" interval="T#10ms" priority="0"><pouInstance name="inst0" typeName="g_comb_or" /></task></resource></configuration></configurations></instances>
</project>
