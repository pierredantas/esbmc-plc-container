<?xml version="1.0" encoding="UTF-8"?>
<!-- FBD body wiring TRUE to both A and B: P1 is violated every scan. -->
<project xmlns="http://www.plcopen.org/xml/tc6_0200">
  <fileHeader companyName="SAFE-LD" productVersion="1.0" creationDateTime="2026-08-27"/>
  <contentHeader name="Mutex"/>
  <types/>
  <instances/>
  <pous>
    <pou name="Mutex" pouType="program">
      <interface>
        <outputVars>
          <variable name="A"><type><BOOL/></type></variable>
          <variable name="B"><type><BOOL/></type></variable>
        </outputVars>
      </interface>
      <body>
        <IL>
          <inVariable localId="1"><expression>TRUE</expression></inVariable>
          <outVariable localId="2">
            <connectionPointIn><connection refLocalId="1"/></connectionPointIn>
            <expression>A</expression></outVariable>
          <outVariable localId="3">
            <connectionPointIn><connection refLocalId="1"/></connectionPointIn>
            <expression>B</expression></outVariable>
        </IL>
      </body>
    </pou>
  </pous>
</project>
