<?xml version="1.0" encoding="utf-8"?>
<!-- Batch reactor overpressure trip voted two out of three pressure switches.
     trip := (ps1 AND ps2) OR (ps2 AND ps3) OR (ps1 AND ps3)
     One stuck-high switch must not trip production; two genuine highs must
     trip, or the vessel stays pressurised behind a closed relief path. -->
<project xmlns="http://www.plcopen.org/xml/tc6_0200">
  <fileHeader companyName="Anonymous" productName="Benchmark Suite" productVersion="1.0" creationDateTime="2026-08-26T00:00:00" />
  <contentHeader name="fbd_reactor_2oo3_clean">
    <coordinateInfo><fbd><scaling x="1" y="1" /></fbd><ld><scaling x="1" y="1" /></ld><sfc><scaling x="1" y="1" /></sfc></coordinateInfo>
  </contentHeader>
  <types>
    <dataTypes />
    <pous>
      <pou name="trip_logic" pouType="program">
        <interface>
          <inputVars>
            <variable name="ps1"><type><BOOL /></type></variable>
            <variable name="ps2"><type><BOOL /></type></variable>
            <variable name="ps3"><type><BOOL /></type></variable>
          </inputVars>
          <outputVars>
            <variable name="trip"><type><BOOL /></type></variable>
          </outputVars>
        </interface>
        <body>
          <FBD>
            <inVariable localId="1" height="20" width="80">
              <position x="20" y="20" />
              <connectionPointOut><relPosition x="80" y="10" /></connectionPointOut>
              <expression>ps1</expression>
            </inVariable>
            <inVariable localId="2" height="20" width="80">
              <position x="20" y="80" />
              <connectionPointOut><relPosition x="80" y="10" /></connectionPointOut>
              <expression>ps2</expression>
            </inVariable>
            <inVariable localId="3" height="20" width="80">
              <position x="20" y="140" />
              <connectionPointOut><relPosition x="80" y="10" /></connectionPointOut>
              <expression>ps3</expression>
            </inVariable>
            <block localId="4" width="60" height="60" typeName="AND">
              <position x="160" y="20" />
              <inputVariables>
                <variable formalParameter="IN1">
                  <connectionPointIn><relPosition x="0" y="20" /><connection refLocalId="1" ><position x="0" y="0" /><position x="0" y="0" /></connection></connectionPointIn>
                </variable>
                <variable formalParameter="IN2">
                  <connectionPointIn><relPosition x="0" y="40" /><connection refLocalId="2" ><position x="0" y="0" /><position x="0" y="0" /></connection></connectionPointIn>
                </variable>
              </inputVariables>
              <inOutVariables />
              <outputVariables>
                <variable formalParameter="OUT">
                  <connectionPointOut><relPosition x="60" y="20" /></connectionPointOut>
                </variable>
              </outputVariables>
            </block>
            <block localId="5" width="60" height="60" typeName="AND">
              <position x="160" y="90" />
              <inputVariables>
                <variable formalParameter="IN1">
                  <connectionPointIn><relPosition x="0" y="20" /><connection refLocalId="2" ><position x="0" y="0" /><position x="0" y="0" /></connection></connectionPointIn>
                </variable>
                <variable formalParameter="IN2">
                  <connectionPointIn><relPosition x="0" y="40" /><connection refLocalId="3" ><position x="0" y="0" /><position x="0" y="0" /></connection></connectionPointIn>
                </variable>
              </inputVariables>
              <inOutVariables />
              <outputVariables>
                <variable formalParameter="OUT">
                  <connectionPointOut><relPosition x="60" y="20" /></connectionPointOut>
                </variable>
              </outputVariables>
            </block>
            <block localId="6" width="60" height="60" typeName="AND">
              <position x="160" y="160" />
              <inputVariables>
                <variable formalParameter="IN1">
                  <connectionPointIn><relPosition x="0" y="20" /><connection refLocalId="1" ><position x="0" y="0" /><position x="0" y="0" /></connection></connectionPointIn>
                </variable>
                <variable formalParameter="IN2">
                  <connectionPointIn><relPosition x="0" y="40" /><connection refLocalId="3" ><position x="0" y="0" /><position x="0" y="0" /></connection></connectionPointIn>
                </variable>
              </inputVariables>
              <inOutVariables />
              <outputVariables>
                <variable formalParameter="OUT">
                  <connectionPointOut><relPosition x="60" y="20" /></connectionPointOut>
                </variable>
              </outputVariables>
            </block>
            <block localId="7" width="60" height="80" typeName="OR">
              <position x="300" y="60" />
              <inputVariables>
                <variable formalParameter="IN1">
                  <connectionPointIn><relPosition x="0" y="20" /><connection refLocalId="4" formalParameter="OUT" ><position x="0" y="0" /><position x="0" y="0" /></connection></connectionPointIn>
                </variable>
                <variable formalParameter="IN2">
                  <connectionPointIn><relPosition x="0" y="40" /><connection refLocalId="5" formalParameter="OUT" ><position x="0" y="0" /><position x="0" y="0" /></connection></connectionPointIn>
                </variable>
                <variable formalParameter="IN3">
                  <connectionPointIn><relPosition x="0" y="60" /><connection refLocalId="6" formalParameter="OUT" ><position x="0" y="0" /><position x="0" y="0" /></connection></connectionPointIn>
                </variable>
              </inputVariables>
              <inOutVariables />
              <outputVariables>
                <variable formalParameter="OUT">
                  <connectionPointOut><relPosition x="60" y="20" /></connectionPointOut>
                </variable>
              </outputVariables>
            </block>
            <outVariable localId="8" height="20" width="80">
              <position x="440" y="80" />
              <connectionPointIn><relPosition x="0" y="10" /><connection refLocalId="7" formalParameter="OUT" ><position x="0" y="0" /><position x="0" y="0" /></connection></connectionPointIn>
              <expression>trip</expression>
            </outVariable>
          </FBD>
        </body>
      </pou>
    </pous>
  </types>
  <instances>
    <configurations>
      <configuration name="Config0">
        <resource name="Res0">
          <task name="tcyclic" interval="T#10ms" priority="0">
            <pouInstance name="inst0" typeName="trip_logic" />
          </task>
        </resource>
      </configuration>
    </configurations>
  </instances>
</project>
