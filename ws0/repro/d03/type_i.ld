<?xml version="1.0" encoding="utf-8"?>
<project xmlns="http://www.plcopen.org/xml/tc6_0200" xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <fileHeader companyName="Anonymous" productName="Benchmark Suite" productVersion="1.0" creationDateTime="2026-08-28T00:00:00" />
  <contentHeader name="g_two_hand_fb_type_i"><coordinateInfo><fbd><scaling x="1" y="1" /></fbd><ld><scaling x="1" y="1" /></ld><sfc><scaling x="1" y="1" /></sfc></coordinateInfo></contentHeader>
  <types><dataTypes /><pous>
    <pou name="TwoHandII" pouType="functionBlock">
      <interface>
        <inputVars><variable name="LH"><type><BOOL /></type></variable><variable name="RH"><type><BOOL /></type></variable></inputVars>
        <outputVars><variable name="Stroke"><type><BOOL /></type></variable></outputVars>
        <localVars><variable name="BothOff"><type><BOOL /></type></variable><variable name="Armed"><type><BOOL /></type></variable></localVars>
      </interface>
      <body><ST><xhtml:p><![CDATA[Stroke := LH AND RH;
]]></xhtml:p></ST></body>
    </pou>
    <pou name="g_two_hand_fb_type_i" pouType="program">
      <interface><inputVars><variable name="LH"><type><BOOL /></type></variable><variable name="RH"><type><BOOL /></type></variable></inputVars><outputVars><variable name="Stroke"><type><BOOL /></type></variable></outputVars></interface>
      <body><LD>
        <leftPowerRail localId="0"><position x="0" y="0" /><connectionPointOut formalParameter="none" /></leftPowerRail>
        <inVariable localId="3" height="20" width="60"><position x="20" y="30" /><connectionPointOut><relPosition x="60" y="10" /></connectionPointOut><expression>LH</expression></inVariable>
        <inVariable localId="4" height="20" width="60"><position x="20" y="60" /><connectionPointOut><relPosition x="60" y="10" /></connectionPointOut><expression>RH</expression></inVariable>
        <block localId="5" width="120" height="80" typeName="TwoHandII" instanceName="THC0">
          <position x="100" y="10" />
          <inputVariables>
            <variable formalParameter="EN"><connectionPointIn><relPosition x="0" y="10" /><connection refLocalId="0" /></connectionPointIn></variable>
            <variable formalParameter="LH"><connectionPointIn><relPosition x="0" y="40" /><connection refLocalId="3" /></connectionPointIn></variable>
            <variable formalParameter="RH"><connectionPointIn><relPosition x="0" y="70" /><connection refLocalId="4" /></connectionPointIn></variable>
          </inputVariables>
          <inOutVariables />
          <outputVariables>
            <variable formalParameter="ENO"><connectionPointOut><relPosition x="120" y="10" /></connectionPointOut></variable>
            <variable formalParameter="Stroke"><connectionPointOut><relPosition x="120" y="40" /></connectionPointOut></variable>
          </outputVariables>
        </block>
        <outVariable localId="6" height="20" width="60" negated="false"><position x="260" y="40" /><connectionPointIn><relPosition x="0" y="10" /><connection refLocalId="5" formalParameter="Stroke" /></connectionPointIn><expression>Stroke</expression></outVariable>
        <rightPowerRail localId="2147483646"><position x="400" y="0" /><connectionPointIn /></rightPowerRail>
      </LD></body>
    </pou>
  </pous></types>
  <instances><configurations><configuration name="Config0"><resource name="Res0"><task name="tcyclic" interval="T#10ms" priority="0"><pouInstance name="inst0" typeName="g_two_hand_fb_type_i" /></task></resource></configuration></configurations></instances>
</project>
