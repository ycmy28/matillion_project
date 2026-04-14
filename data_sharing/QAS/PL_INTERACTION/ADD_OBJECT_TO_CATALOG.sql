call DB_FRAMEWORK.UTILS.SP_ADD_OBJECT_TO_CATALOG(
	'DB_CONS_PL_QAS.PL_INTERACTION.DIM_BRIDGE_CNPS_SURVEY',			-- SOURCE_OBJECT
	'PRESENTATION',                             						-- OBJECT_DATA_LAYER
	'INTERNAL',                             							-- OBJECT_DATA_CLASSIFICATION
	'NO',                                       						-- OBJECT_HAS_PERSONAL_DATA
	'Evgeniy.Gussman@pmi.com',                       		            -- DATA_OWNER
	'Anna.Martin@pmi.com',                        				-- DATA_STEWARD
	'Dimension table storing attributes describing a particular survey which has been filled out.',                			-- DATASET_DESCRIPTION
	'Daily',                                  							-- DATASET_REFRESH_INFORMATION
	'ALL',                               								-- DATASET_TIME_RANGE_COVERED
	'CONS',                                     						-- DOMAIN
	'COLUMN',												-- RLS_TYPE
	'COUNTRY_CODE'                                						-- RLS_COLUMN
);
call DB_FRAMEWORK.UTILS.SP_ADD_OBJECT_TO_CATALOG(
	'DB_CONS_PL_QAS.PL_INTERACTION.DIM_CNPS_CALLBACK_OWNER',			-- SOURCE_OBJECT
	'PRESENTATION',                             						-- OBJECT_DATA_LAYER
	'INTERNAL',                             							-- OBJECT_DATA_CLASSIFICATION
	'YES',                                       						-- OBJECT_HAS_PERSONAL_DATA
	'Evgeniy.Gussman@pmi.com',                       		            -- DATA_OWNER
	'Anna.Martin@pmi.com',                        				-- DATA_STEWARD
	'Dimension table storing name of person owning and managing a particular ticket/callback. In Qualtrics, the ticket owner is the person responsible for managing and resolving a specific ticket. This role is crucial in ensuring accountability and timely follow-up on customer issues or feedback.',                			-- DATASET_DESCRIPTION
	'Daily',                                  							-- DATASET_REFRESH_INFORMATION
	'ALL',                               								-- DATASET_TIME_RANGE_COVERED
	'CONS',                                     						-- DOMAIN
	'',												-- RLS_TYPE
	''                                						-- RLS_COLUMN
);
call DB_FRAMEWORK.UTILS.SP_ADD_OBJECT_TO_CATALOG(
	'DB_CONS_PL_QAS.PL_INTERACTION.DIM_CNPS_CALLBACK_PRIORITY',			-- SOURCE_OBJECT
	'PRESENTATION',                             						-- OBJECT_DATA_LAYER
	'INTERNAL',                             							-- OBJECT_DATA_CLASSIFICATION
	'NO',                                       						-- OBJECT_HAS_PERSONAL_DATA
	'Evgeniy.Gussman@pmi.com',                       		            -- DATA_OWNER
	'Anna.Martin@pmi.com',                        				-- DATA_STEWARD
	'Dimension table storing callback priority possible values. In Qualtrics, ticket priority refers to the level of urgency or importance assigned to a ticket within a ticketing workflow. It helps teams determine how quickly a ticket should be addressed and which tickets need immediate attention. LoV: High, Medium or Low',                			-- DATASET_DESCRIPTION
	'Daily',                                  							-- DATASET_REFRESH_INFORMATION
	'ALL',                               								-- DATASET_TIME_RANGE_COVERED
	'CONS',                                     						-- DOMAIN
	'',												-- RLS_TYPE
	''                                						-- RLS_COLUMN
);
call DB_FRAMEWORK.UTILS.SP_ADD_OBJECT_TO_CATALOG(
	'DB_CONS_PL_QAS.PL_INTERACTION.DIM_CNPS_CALLBACK_ROOT_CAUSE',			-- SOURCE_OBJECT
	'PRESENTATION',                             						-- OBJECT_DATA_LAYER
	'INTERNAL',                             							-- OBJECT_DATA_CLASSIFICATION
	'NO',                                       						-- OBJECT_HAS_PERSONAL_DATA
	'Evgeniy.Gussman@pmi.com',                       		            -- DATA_OWNER
	'Anna.Martin@pmi.com',                        				-- DATA_STEWARD
	'Dimension table storing all possible roout cause for a callback/ticket. In Qualtrics, the root cause in a ticket refers to the underlying reason or primary factor that led to the issue or feedback captured in the ticket. Identifying the root cause helps in understanding why a problem occurred and how to prevent it in the future.',                			-- DATASET_DESCRIPTION
	'Daily',                                  							-- DATASET_REFRESH_INFORMATION
	'ALL',                               								-- DATASET_TIME_RANGE_COVERED
	'CONS',                                     						-- DOMAIN
	'',												-- RLS_TYPE
	''                                						-- RLS_COLUMN
);
call DB_FRAMEWORK.UTILS.SP_ADD_OBJECT_TO_CATALOG(
	'DB_CONS_PL_QAS.PL_INTERACTION.DIM_CNPS_CALLBACK_STATUS',			-- SOURCE_OBJECT
	'PRESENTATION',                             						-- OBJECT_DATA_LAYER
	'INTERNAL',                             							-- OBJECT_DATA_CLASSIFICATION
	'NO',                                       						-- OBJECT_HAS_PERSONAL_DATA
	'Evgeniy.Gussman@pmi.com',                       		            -- DATA_OWNER
	'Anna.Martin@pmi.com',                        				-- DATA_STEWARD
	'Dimension table storing all possible callback statuses. In Qualtrics, a ticket status indicates the current stage or progress of a ticket within a ticketing workflow. It helps teams track and manage customer issues or feedback efficiently.',                			-- DATASET_DESCRIPTION
	'Daily',                                  							-- DATASET_REFRESH_INFORMATION
	'ALL',                               								-- DATASET_TIME_RANGE_COVERED
	'CONS',                                     						-- DOMAIN
	'',												-- RLS_TYPE
	''                                						-- RLS_COLUMN
);
call DB_FRAMEWORK.UTILS.SP_ADD_OBJECT_TO_CATALOG(
	'DB_CONS_PL_QAS.PL_INTERACTION.DIM_CNPS_CALLBACK_TEAM',			-- SOURCE_OBJECT
	'PRESENTATION',                             						-- OBJECT_DATA_LAYER
	'INTERNAL',                             							-- OBJECT_DATA_CLASSIFICATION
	'NO',                                       						-- OBJECT_HAS_PERSONAL_DATA
	'Evgeniy.Gussman@pmi.com',                       		            -- DATA_OWNER
	'Anna.Martin@pmi.com',                        				-- DATA_STEWARD
	'Dimension table storing Teams responsible for processing callback tickets. In Qualtrics, a team in the context of tickets refers to a group of users who can collectively manage and respond to tickets within a ticketing project. Teams help organize ticket ownership and streamline workflows by assigning tickets to groups rather than individuals.',                			-- DATASET_DESCRIPTION
	'Daily',                                  							-- DATASET_REFRESH_INFORMATION
	'ALL',                               								-- DATASET_TIME_RANGE_COVERED
	'CONS',                                     						-- DOMAIN
	'',												-- RLS_TYPE
	''                                						-- RLS_COLUMN
);
call DB_FRAMEWORK.UTILS.SP_ADD_OBJECT_TO_CATALOG(
	'DB_CONS_PL_QAS.PL_INTERACTION.DIM_CNPS_CONSUMER_PROGRAM',			-- SOURCE_OBJECT
	'PRESENTATION',                             						-- OBJECT_DATA_LAYER
	'INTERNAL',                             							-- OBJECT_DATA_CLASSIFICATION
	'NO',                                       						-- OBJECT_HAS_PERSONAL_DATA
	'Evgeniy.Gussman@pmi.com',                       		            -- DATA_OWNER
	'Anna.Martin@pmi.com',                        				-- DATA_STEWARD
	'Dimension table storing attributes describing Consumer Programs that are linked to conducted Surveys',                			-- DATASET_DESCRIPTION
	'Daily',                                  							-- DATASET_REFRESH_INFORMATION
	'ALL',                               								-- DATASET_TIME_RANGE_COVERED
	'CONS',                                     						-- DOMAIN
	'',												-- RLS_TYPE
	''                                						-- RLS_COLUMN
);
call DB_FRAMEWORK.UTILS.SP_ADD_OBJECT_TO_CATALOG(
	'DB_CONS_PL_QAS.PL_INTERACTION.DIM_CNPS_SEGMENT',			-- SOURCE_OBJECT
	'PRESENTATION',                             						-- OBJECT_DATA_LAYER
	'INTERNAL',                             							-- OBJECT_DATA_CLASSIFICATION
	'NO',                                       						-- OBJECT_HAS_PERSONAL_DATA
	'Evgeniy.Gussman@pmi.com',                       		            -- DATA_OWNER
	'Anna.Martin@pmi.com',                        				-- DATA_STEWARD
	'Dimension storing CNPS segments. Segment assigne Consumers taking part in Surveys to three groups: Detractor, Passive, Promoter',                			-- DATASET_DESCRIPTION
	'Daily',                                  							-- DATASET_REFRESH_INFORMATION
	'ALL',                               								-- DATASET_TIME_RANGE_COVERED
	'CONS',                                     						-- DOMAIN
	'',												-- RLS_TYPE
	''                                						-- RLS_COLUMN
);
call DB_FRAMEWORK.UTILS.SP_ADD_OBJECT_TO_CATALOG(
	'DB_CONS_PL_QAS.PL_INTERACTION.DIM_CNPS_SENTIMENT',			-- SOURCE_OBJECT
	'PRESENTATION',                             						-- OBJECT_DATA_LAYER
	'INTERNAL',                             							-- OBJECT_DATA_CLASSIFICATION
	'NO',                                       						-- OBJECT_HAS_PERSONAL_DATA
	'Evgeniy.Gussman@pmi.com',                       		            -- DATA_OWNER
	'Anna.Martin@pmi.com',                        				-- DATA_STEWARD
	'Dimension storing CNPS Sentiments.Very Negative, Negative, Mixed, Positive,Very Positive',                			-- DATASET_DESCRIPTION
	'Daily',                                  							-- DATASET_REFRESH_INFORMATION
	'ALL',                               								-- DATASET_TIME_RANGE_COVERED
	'CONS',                                     						-- DOMAIN
	'',												-- RLS_TYPE
	''                                						-- RLS_COLUMN
);
call DB_FRAMEWORK.UTILS.SP_ADD_OBJECT_TO_CATALOG(
	'DB_CONS_PL_QAS.PL_INTERACTION.DIM_CNPS_SURVEY',			-- SOURCE_OBJECT
	'PRESENTATION',                             						-- OBJECT_DATA_LAYER
	'INTERNAL',                             							-- OBJECT_DATA_CLASSIFICATION
	'NO',                                       						-- OBJECT_HAS_PERSONAL_DATA
	'Evgeniy.Gussman@pmi.com',                       		            -- DATA_OWNER
	'Anna.Martin@pmi.com',                        				-- DATA_STEWARD
	'Dimension table storing attributes describing a particular survey which has been filled out.',                			-- DATASET_DESCRIPTION
	'Daily',                                  							-- DATASET_REFRESH_INFORMATION
	'ALL',                               								-- DATASET_TIME_RANGE_COVERED
	'CONS',                                     						-- DOMAIN
	'',												-- RLS_TYPE
	''                                						-- RLS_COLUMN
);
call DB_FRAMEWORK.UTILS.SP_ADD_OBJECT_TO_CATALOG(
	'DB_CONS_PL_QAS.PL_INTERACTION.DIM_CNPS_SURVEY_CHANNEL',			-- SOURCE_OBJECT
	'PRESENTATION',                             						-- OBJECT_DATA_LAYER
	'INTERNAL',                             							-- OBJECT_DATA_CLASSIFICATION
	'NO',                                       						-- OBJECT_HAS_PERSONAL_DATA
	'Evgeniy.Gussman@pmi.com',                       		            -- DATA_OWNER
	'Anna.Martin@pmi.com',                        				-- DATA_STEWARD
	'Dimension table storing attributes describing CHANNEL through which the Survey was conducted',                			-- DATASET_DESCRIPTION
	'Daily',                                  							-- DATASET_REFRESH_INFORMATION
	'ALL',                               								-- DATASET_TIME_RANGE_COVERED
	'CONS',                                     						-- DOMAIN
	'',												-- RLS_TYPE
	''                                						-- RLS_COLUMN
);
call DB_FRAMEWORK.UTILS.SP_ADD_OBJECT_TO_CATALOG(
	'DB_CONS_PL_QAS.PL_INTERACTION.DIM_CNPS_SURVEY_RESPONSE',			-- SOURCE_OBJECT
	'PRESENTATION',                             						-- OBJECT_DATA_LAYER
	'HIGHLY_CONFIDENTIAL',                             							-- OBJECT_DATA_CLASSIFICATION
	'YES',                                       						-- OBJECT_HAS_PERSONAL_DATA
	'Evgeniy.Gussman@pmi.com',                       		            -- DATA_OWNER
	'Anna.Martin@pmi.com',                        				-- DATA_STEWARD
	'Response table sourced from V_QUALTRICS_CNPS_SURVEY',                			-- DATASET_DESCRIPTION
	'Daily',                                  							-- DATASET_REFRESH_INFORMATION
	'ALL',                               								-- DATASET_TIME_RANGE_COVERED
	'CONS',                                     						-- DOMAIN
	'',												-- RLS_TYPE
	''                                						-- RLS_COLUMN
);
call DB_FRAMEWORK.UTILS.SP_ADD_OBJECT_TO_CATALOG(
	'DB_CONS_PL_QAS.PL_INTERACTION.DIM_CNPS_TOPIC_TAXONOMY',			-- SOURCE_OBJECT
	'PRESENTATION',                             						-- OBJECT_DATA_LAYER
	'INTERNAL',                             							-- OBJECT_DATA_CLASSIFICATION
	'NO',                                       						-- OBJECT_HAS_PERSONAL_DATA
	'Evgeniy.Gussman@pmi.com',                       		            -- DATA_OWNER
	'Anna.Martin@pmi.com',                        				-- DATA_STEWARD
	'Dimension stands for a dictionary of all topics ',                			-- DATASET_DESCRIPTION
	'Daily',                                  							-- DATASET_REFRESH_INFORMATION
	'ALL',                               								-- DATASET_TIME_RANGE_COVERED
	'CONS',                                     						-- DOMAIN
	'',												-- RLS_TYPE
	''                                						-- RLS_COLUMN
);
call DB_FRAMEWORK.UTILS.SP_ADD_OBJECT_TO_CATALOG(
	'DB_CONS_PL_QAS.PL_INTERACTION.DIM_CNPS_TOUCHPOINT',			-- SOURCE_OBJECT
	'PRESENTATION',                             						-- OBJECT_DATA_LAYER
	'INTERNAL',                             							-- OBJECT_DATA_CLASSIFICATION
	'NO',                                       						-- OBJECT_HAS_PERSONAL_DATA
	'Evgeniy.Gussman@pmi.com',                       		            -- DATA_OWNER
	'Anna.Martin@pmi.com',                        				-- DATA_STEWARD
	'Dimension table storing TOUCHPOINT attributes - reason the Survey was conducted',                			-- DATASET_DESCRIPTION
	'Daily',                                  							-- DATASET_REFRESH_INFORMATION
	'ALL',                               								-- DATASET_TIME_RANGE_COVERED
	'CONS',                                     						-- DOMAIN
	'',												-- RLS_TYPE
	''                                						-- RLS_COLUMN
);
call DB_FRAMEWORK.UTILS.SP_ADD_OBJECT_TO_CATALOG(
	'DB_CONS_PL_QAS.PL_INTERACTION.FACT_CNPS_CALLBACK',			-- SOURCE_OBJECT
	'PRESENTATION',                             						-- OBJECT_DATA_LAYER
	'INTERNAL',                             							-- OBJECT_DATA_CLASSIFICATION
	'NO',                                       						-- OBJECT_HAS_PERSONAL_DATA
	'Evgeniy.Gussman@pmi.com',                       		            -- DATA_OWNER
	'Anna.Martin@pmi.com',                        				-- DATA_STEWARD
	'Fact table storing callbacks - tickets triggered by received feedback through filled out survey by Consumer. Tickets help to respond to customer feedback efficiently by turning survey responses into actionable tasks.',                			-- DATASET_DESCRIPTION
	'Daily',                                  							-- DATASET_REFRESH_INFORMATION
	'ALL',                               								-- DATASET_TIME_RANGE_COVERED
	'CONS',                                     						-- DOMAIN
	'COLUMN',												-- RLS_TYPE
	'COUNTRY_CODE'                                						-- RLS_COLUMN
);
call DB_FRAMEWORK.UTILS.SP_ADD_OBJECT_TO_CATALOG(
	'DB_CONS_PL_QAS.PL_INTERACTION.FACT_CNPS_RESPONSE_TOPIC',			-- SOURCE_OBJECT
	'PRESENTATION',                             						-- OBJECT_DATA_LAYER
	'INTERNAL',                             							-- OBJECT_DATA_CLASSIFICATION
	'NO',                                       						-- OBJECT_HAS_PERSONAL_DATA
	'Evgeniy.Gussman@pmi.com',                       		            -- DATA_OWNER
	'Anna.Martin@pmi.com',                        				-- DATA_STEWARD
	'Fact table containing topics assigned to a specific verbatim within a particular survey response (brand, channel, program, ces, combined). Topics are standardized in a predefined list and organized in a hierarchies with levels from 1 to 3 (available in topic dimension). ',                			-- DATASET_DESCRIPTION
	'Daily',                                  							-- DATASET_REFRESH_INFORMATION
	'ALL',                               								-- DATASET_TIME_RANGE_COVERED
	'CONS',                                     						-- DOMAIN
	'COLUMN',												-- RLS_TYPE
	'COUNTRY_CODE'                                						-- RLS_COLUMN
);