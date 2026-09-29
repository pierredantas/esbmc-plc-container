<?xml version="1.0" encoding="utf-8"?>
<project xmlns="http://www.plcopen.org/xml/tc6_0200">
  <fileHeader companyName="Anonymous" productName="repro" productVersion="1.0" creationDateTime="2026-09-26T00:00:00" />
  <contentHeader name="oneshot"><coordinateInfo><fbd><scaling x="1" y="1" /></fbd><ld><scaling x="1" y="1" /></ld><sfc><scaling x="1" y="1" /></sfc></coordinateInfo></contentHeader>
  <types><dataTypes /><pous><pou name="oneshot" pouType="program">
    <interface>
      <inputVars><variable name="Sig"><type><BOOL /></type></variable></inputVars>
      <outputVars><variable name="OneShot"><type><BOOL /></type></variable></outputVars>
      <localVars><variable name="Rise"><type><BOOL /></type></variable><variable name="Sig_prev"><type><BOOL /></type></variable></localVars>
    </interface>
    <body><LD>
      <leftPowerRail localId="0"><position x="0" y="0" /><connectionPointOut formalParameter="none" /></leftPowerRail>
      <contact localId="1" negated="false" storage="none" edge="none"><position x="20" y="10" /><connectionPointIn><connection refLocalId="0" /></connectionPointIn><connectionPointOut /><variable>Sig</variable></contact>
      <contact localId="2" negated="true" storage="none" edge="none"><position x="50" y="10" /><connectionPointIn><connection refLocalId="1" /></connectionPointIn><connectionPointOut /><variable>Sig_prev</variable></contact>
      <coil localId="5" negated="false" storage="none"><position x="100" y="10" /><connectionPointIn><connection refLocalId="2" /></connectionPointIn><connectionPointOut /><variable>Rise</variable></coil>
      <contact localId="6" negated="false" storage="none" edge="none"><position x="20" y="40" /><connectionPointIn><connection refLocalId="0" /></connectionPointIn><connectionPointOut /><variable>Rise</variable></contact>
      <coil localId="7" negated="false" storage="none"><position x="100" y="40" /><connectionPointIn><connection refLocalId="6" /></connectionPointIn><connectionPointOut /><variable>OneShot</variable></coil>
      <contact localId="8" negated="false" storage="none" edge="none"><position x="20" y="70" /><connectionPointIn><connection refLocalId="0" /></connectionPointIn><connectionPointOut /><variable>Sig</variable></contact>
      <coil localId="9" negated="false" storage="none"><position x="100" y="70" /><connectionPointIn><connection refLocalId="8" /></connectionPointIn><connectionPointOut /><variable>Sig_prev</variable></coil>
      <rightPowerRail localId="2147483646"><position x="400" y="0" /><connectionPointIn /></rightPowerRail>
    </LD></body>
  </pou></pous></types>
  <instances><configurations><configuration name="Config0"><resource name="Res0"><task name="tcyclic" interval="T#10ms" priority="0"><pouInstance name="inst0" typeName="oneshot" /></task></resource></configuration></configurations></instances>
</project>
