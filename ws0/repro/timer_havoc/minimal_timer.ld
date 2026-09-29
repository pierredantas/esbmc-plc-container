<?xml version="1.0" encoding="UTF-8"?>
<!-- Minimal timer probe: Light is driven solely by a TON done-bit. -->
<!-- Btn -> T_IN ; TON(T_IN,PT)->T_Q ; T_Q -> Light -->
<project xmlns="http://www.plcopen.org/xml/tc6_0200">
  <fileHeader companyName="probe" productVersion="1.0" creationDateTime="2026-07-01"/>
  <contentHeader name="Minimal_Timer"/>
  <types/>
  <instances>
    <configurations>
      <configuration name="Config">
        <resource name="Resource">
          <task name="MainTask" priority="0" interval="T#10ms"/>
          <pouInstance name="MT" typeName="Minimal_Timer"/>
        </resource>
      </configuration>
    </configurations>
  </instances>
  <pous>
    <pou name="Minimal_Timer" pouType="program">
      <interface>
        <inputVars>
          <variable name="Btn"><type><BOOL/></type></variable>
        </inputVars>
        <outputVars>
          <variable name="Light"><type><BOOL/></type></variable>
        </outputVars>
        <localVars>
          <variable name="T_IN"><type><BOOL/></type></variable>
          <variable name="T_Q"><type><BOOL/></type></variable>
          <variable name="T_ET"><type><INT/></type></variable>
          <variable name="T_PT"><type><INT/></type></variable>
        </localVars>
      </interface>
      <body>
        <LD>
          <rung localId="1" lineNumber="1">
            <contact variable="Btn"/>
            <coil variable="T_IN"/>
          </rung>
          <rung localId="2" lineNumber="2">
            <block typeName="TON" instanceName="T" lineNumber="2">
              <variable formalParameter="IN">T_IN</variable>
              <variable formalParameter="PT">T_PT</variable>
              <variable formalParameter="Q">T_Q</variable>
              <variable formalParameter="ET">T_ET</variable>
            </block>
          </rung>
          <rung localId="3" lineNumber="3">
            <contact variable="T_Q"/>
            <coil variable="Light"/>
          </rung>
        </LD>
      </body>
    </pou>
  </pous>
</project>
